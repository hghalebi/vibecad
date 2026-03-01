import os
import re
import subprocess

def get_num(filename):
    match = re.search(r'render_(\d+)\.png', filename)
    return int(match.group(1)) if match else -1

def create_animation(input_dir, output_file, fps=2):
    # Find and sort all relevant images
    images = [img for img in os.listdir(input_dir) if img.startswith("render_") and img.endswith(".png")]
    images.sort(key=get_num)
    
    if not images:
        print("No render images found.")
        return

    print(f"Found {len(images)} images. Creating animation using ffmpeg...")

    # Create a temporary file list for the ffmpeg concat demuxer
    # This is more robust than shell globbing or assuming sequential numbering
    list_file = "ffmpeg_list.txt"
    with open(list_file, "w") as f:
        # Each entry consists of the file path and its duration in seconds (1/fps)
        duration = 1.0 / fps
        for image in images:
            image_path = os.path.abspath(os.path.join(input_dir, image))
            f.write(f"file '{image_path}'\n")
            f.write(f"duration {duration}\n")
        
        # Hold the last frame for 2 additional seconds
        last_image_path = os.path.abspath(os.path.join(input_dir, images[-1]))
        f.write(f"file '{last_image_path}'\n")
        f.write(f"duration 2.0\n")

    # Construct the ffmpeg command
    # -y: overwrite output
    # -f concat: use the concat demuxer
    # -safe 0: allow absolute paths
    # -i {list_file}: use the generated file list
    # -pix_fmt yuv420p: use a widely compatible pixel format for MP4
    cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_file,
        "-pix_fmt", "yuv420p", output_file
    ]

    print(f"Running command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print(f"Animation successfully saved to {output_file}")
    except subprocess.CalledProcessError as e:
        print(f"Error during ffmpeg execution:\n{e.stderr}")
    finally:
        # Clean up the temporary list file
        if os.path.exists(list_file):
            os.remove(list_file)

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python create_agent_animation.py <directory_path>")
        sys.exit(1)
    
    input_directory = sys.argv[1].rstrip("/")
    # Use the directory name for the output file
    dir_name = os.path.basename(input_directory)
    output_filename = f"{dir_name}.mp4"
    
    if not os.path.isdir(input_directory):
        print(f"Error: {input_directory} is not a directory.")
        sys.exit(1)
        
    create_animation(input_directory, output_filename)
