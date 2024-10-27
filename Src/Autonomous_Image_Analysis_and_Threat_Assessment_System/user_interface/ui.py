import tkinter as tk

from user_interface.event_handlers import EventHandlers
from process_operations.video_processor import VideoProcessor
from object_detection.object_detector import ObjectDetector

class application:
    def __init__(self, root):
        self.root = root
        self.root.title("System User Interface")

        # Define fixed window size and center it
        self.window_width = 1600
        self.window_height = 930
        self.center_window(self.window_width, self.window_height)

        # Prevent window from being resized
        self.root.resizable(False, False)

        # Set a modern background color
        self.root.configure(bg="#2C3E50")

        # Define a consistent font
        self.default_font = ("Helvetica", 12)

        # Main frame with 3 columns
        self.main_frame = tk.Frame(self.root, bg="#34495E", bd=5, relief=tk.RIDGE)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Configure main_frame to have 3 columns
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_columnconfigure(1, weight=1)
        self.main_frame.grid_columnconfigure(2, weight=1)  # Third column for spacing

        # Video control variables
        self.playing = False
        self.video_path = ""
        self.cap = None
        self.fps = 0
        self.direction = 1  # 1 forward, -1 reverse
        self.frame_skip = 1  # Process every frame
        self.current_frame = 0
        self.processing = False
        self.video_thread_running = False  # Flag to prevent multiple threads

        # Video info label spanning first two columns
        self.video_info_label = tk.Label(
            self.main_frame,
            text="No video selected.",
            bg="#34495E",
            fg="white",
            font=self.default_font,
            anchor="w"
        )
        self.video_info_label.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))

        # Add empty space in the third column of the first row
        self.empty_space_label = tk.Label(self.main_frame, bg="#34495E")
        self.empty_space_label.grid(row=0, column=2, sticky="ew")

        # Content frame for video and action buttons with 3 columns
        self.content_frame = tk.Frame(self.main_frame, bg="#34495E")
        self.content_frame.grid(row=1, column=0, columnspan=3, sticky="nsew")

        # Configure content_frame to have 3 columns
        self.content_frame.grid_columnconfigure(0, weight=1)
        self.content_frame.grid_columnconfigure(1, weight=1)
        self.content_frame.grid_columnconfigure(2, weight=0)  # Third column for additional spacing

        # Video frame (fixed size)
        self.video_frame_width = 1280
        self.video_frame_height = 720
        self.video_frame = tk.Frame(self.content_frame, bd=2, relief=tk.SUNKEN, bg="black",
                                    width=self.video_frame_width, height=self.video_frame_height)
        self.video_frame.grid(row=0, column=0, padx=10, pady=10)
        self.video_frame.pack_propagate(0)  # Prevent frame from resizing to content

        # Video label
        self.video_label = tk.Label(self.video_frame, bg="black")
        self.video_label.pack(fill=tk.BOTH, expand=True)

        # Action button frame on the right side of the video with additional padding
        self.button_frame = tk.Frame(self.content_frame, bg="#34495E", padx=10, pady=10)
        self.button_frame.grid(row=0, column=1, padx=10, pady=10, sticky="n")

        # Initialize event handlers before creating buttons
        self.event_handlers = EventHandlers(self)

        # Initialize VideoProcessor
        self.video_processor = VideoProcessor(self)

        # Initialize ObjectDetector
        self.object_detector = ObjectDetector()

        # Create action buttons after initializing event_handlers
        self.create_action_buttons()

        # Add empty space in the third column of content_frame for spacing
        self.additional_space_frame = tk.Frame(self.content_frame, bg="#34495E", width=0)
        self.additional_space_frame.grid(row=0, column=2, padx=10, pady=10, sticky="n")

        # Control buttons below the content frame with additional padding
        self.control_frame = tk.Frame(self.main_frame, bg="#34495E", padx=10, pady=10)
        self.control_frame.grid(row=2, column=0, columnspan=3, pady=10, sticky="ew")

        # Create control buttons
        self.create_control_buttons()

    def center_window(self, width, height):
        # Get screen width and height
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        # Calculate position x and y coordinates
        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")

    def create_action_buttons(self):
        # Define action button specifications
        button_specs = [
            ("Select Object", self.event_handlers.select_object, "#2980B9"),
            ("Select Region", self.event_handlers.select_region, "#2980B9"),
            ("Track Object", self.event_handlers.track_object, "#2980B9"),
            ("Untrack Object", self.event_handlers.untrack_object, "#2980B9"),
            ("Mark as Adversary", self.event_handlers.mark_adversary, "#C0392B"),
            ("Mark as Friend", self.event_handlers.mark_friend, "#C0392B"),
            ("Threat Assessment", self.event_handlers.perform_threat_assessment, "#27AE60")
        ]

        for text, command, color in button_specs:
            btn = tk.Button(
                self.button_frame,
                text=text,
                command=command,
                width=25,
                height=2,
                bg=color,
                fg="white",
                bd=0,
                font=self.default_font,
                activebackground=color,
                activeforeground="white",
                cursor="hand2"
            )
            btn.pack(pady=10, anchor='w', padx=(0, 20), fill='x')

    def create_control_buttons(self):
        # Define control button specifications with logical colors
        control_buttons = [
            ("Select Video", self.event_handlers.open_video, "#2980B9"),  # Blue
            ("Play", self.event_handlers.resume_video, "#27AE60"),        # Green
            ("Pause", self.event_handlers.pause_video, "#F1C40F"),       # Yellow
            ("Rewind", self.event_handlers.rewind_video, "#E67E22"),     # Orange
            ("Exit", self.event_handlers.quit_app, "#C0392B")            # Red
        ]

        for idx, (text, command, color) in enumerate(control_buttons):
            btn = tk.Button(
                self.control_frame,
                text=text,
                command=command,
                width=15,
                height=2,
                bg=color,
                fg="white",
                bd=0,
                font=self.default_font,
                activebackground=color,
                activeforeground="white",
                cursor="hand2"
            )
            btn.grid(row=0, column=idx, padx=10, pady=10)
