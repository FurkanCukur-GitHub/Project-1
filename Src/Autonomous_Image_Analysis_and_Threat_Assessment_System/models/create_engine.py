# yolo export model=yolo_model.pt format=onnx dynamic=True device=0

# trtexec --onnx=yolo_model.onnx --saveEngine=yolo_model_b1.engine --optShapes=images:1x3x640x640 --minShapes=images:1x3x640x640 --maxShapes=images:16x3x640x640 --fp16 --memPoolSize=workspace:512
# trtexec --onnx=yolo_model.onnx --saveEngine=yolo_model_b2.engine --optShapes=images:2x3x640x640 --minShapes=images:1x3x640x640 --maxShapes=images:16x3x640x640 --fp16 --memPoolSize=workspace:1024
# trtexec --onnx=yolo_model.onnx --saveEngine=yolo_model_b4.engine --optShapes=images:4x3x640x640 --minShapes=images:1x3x640x640 --maxShapes=images:16x3x640x640 --fp16 --memPoolSize=workspace:2048
# trtexec --onnx=yolo_model.onnx --saveEngine=yolo_model_b8.engine --optShapes=images:8x3x640x640 --minShapes=images:1x3x640x640 --maxShapes=images:16x3x640x640 --fp16 --memPoolSize=workspace:3072
# trtexec --onnx=yolo_model.onnx --saveEngine=yolo_model_b16.engine --optShapes=images:16x3x640x640 --minShapes=images:1x3x640x640 --maxShapes=images:16x3x640x640 --fp16 --memPoolSize=workspace:4096


