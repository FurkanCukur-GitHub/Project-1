# modules/autobackend.py
import contextlib
import json
from collections import OrderedDict, namedtuple
from pathlib import Path
from urllib.parse import urlparse
import tensorrt as trt
import numpy as np
import torch
import torch.nn as nn

from ultralytics.utils import LOGGER, ROOT, yaml_load
from ultralytics.utils.checks import check_yaml, check_version

def check_class_names(names):
    if isinstance(names, list):
        names = dict(enumerate(names))
    if isinstance(names, dict):
        if not all(isinstance(k, int) for k in names.keys()):
            names = {int(k): v for k, v in names.items()}
        if isinstance(names[0], str) and names[0].startswith('n0'):
            map = yaml_load(ROOT / 'datasets/ImageNet.yaml')['map']
            names = {k: map[v] for k, v in names.items()}
    return names

class AutoBackend(nn.Module):
    def _apply_default_class_names(self, data):
        with contextlib.suppress(Exception):
            return yaml_load(check_yaml(data))['names']
        return {i: f'class{i}' for i in range(999)}

    def __init__(self, weights='yolov8n.engine', device=None, data=None, fp16=True):
        super().__init__()
        w = str(weights[0] if isinstance(weights, list) else weights)

        LOGGER.info(f"Loading {w} for TensorRT inference... (fp16={fp16})")

        check_version(trt.__version__, ">=7.0.0", hard=True)
        device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")

        Binding = namedtuple("Binding", ("name", "dtype", "shape", "data", "ptr"))
        logger = trt.Logger(trt.Logger.INFO)

        with open(w, "rb") as f, trt.Runtime(logger) as runtime:
            try:
                meta_len = int.from_bytes(f.read(4), byteorder="little")
                metadata = json.loads(f.read(meta_len).decode("utf-8"))
            except UnicodeDecodeError:
                metadata = {}
                f.seek(0)
            model = runtime.deserialize_cuda_engine(f.read())

        dynamic = False
        
        try:
            context = model.create_execution_context()
        except Exception as e:
            LOGGER.error(f"ERROR: TensorRT model exported with a different version than {trt.__version__}\n")
            raise e

        bindings = OrderedDict()
        output_names = []

        num_tensors = model.num_io_tensors
        for i in range(num_tensors):
            name = model.get_tensor_name(i)
            dtype = trt.nptype(model.get_tensor_dtype(name))
            is_input = (model.get_tensor_mode(name) == trt.TensorIOMode.INPUT)

            if is_input:
                if -1 in tuple(model.get_tensor_shape(name)):
                    dynamic = True
                    profile_shape = model.get_tensor_profile_shape(name, 0)
                    context.set_input_shape(name, tuple(profile_shape[1]))
            else:
                output_names.append(name)

        for i in range(num_tensors):
            name = model.get_tensor_name(i)
            shape = tuple(context.get_tensor_shape(name))
            dtype = trt.nptype(model.get_tensor_dtype(name))
            im = torch.empty(size=shape, dtype=torch.float32, device=device)  
            ptr = im.data_ptr()
            bindings[name] = Binding(name, dtype, shape, im, ptr)

        binding_addrs = OrderedDict((n, d.ptr) for n, d in bindings.items())
        batch_size = bindings["images"].shape[0] if "images" in bindings else 1

        stride = int(metadata['stride']) if 'stride' in metadata else 32
        names = metadata['names'] if 'names' in metadata else self._apply_default_class_names(data)
        names = check_class_names(names)

        self.__dict__.update(locals())

    def forward(self, im, visualize=False):
        b, ch, h, w = im.shape
        if self.fp16 and im.dtype != torch.float32:
            im = im.half()

        # Set dynamic input size
        if self.dynamic and im.shape != self.bindings['images'].shape:
            self.context.set_input_shape('images', im.shape)
            new_tensor = torch.empty(size=im.shape, dtype=torch.float32, device=self.device)
            self.bindings['images'] = self.bindings['images']._replace(
                shape=im.shape, data=new_tensor, ptr=new_tensor.data_ptr()
            )

        self.bindings['images'].data.copy_(im)

        for name, binding in self.bindings.items():
            self.context.set_tensor_address(name, binding.ptr)

        try:
            success = self.context.execute_v2([binding.ptr for binding in self.bindings.values()])
            if not success:
                raise RuntimeError("TensorRT inference execution failed.")
        except Exception as e:
            raise RuntimeError(f"TensorRT execute_v2 failed: {e}")

        outputs = []
        for name in self.output_names:
            tensor = self.bindings[name].data.clone().cpu()
            outputs.append(tensor)

        if len(outputs) == 1:
            return outputs[0]
        return outputs

    def warmup(self, imgsz=(1, 3, 640, 640)):
        if self.device.type != 'cpu':
            im = torch.empty(*imgsz, dtype=torch.half if self.fp16 else torch.float, device=self.device)
            for _ in range(1):
                self.forward(im)