import cv2
import os

def test_video_duration(video_path):
    if not os.path.exists(video_path):
        print(f"Dosya bulunamadı: {video_path}")
        return
    
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Video açılamadı: {video_path}")
        return
    
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()
    
    if fps > 0 and frame_count > 0:
        duration = frame_count / fps
        print(f"Video: {video_path}")
        print(f"FPS: {fps}")
        print(f"Frame Count: {frame_count}")
        print(f"Duration: {duration:.2f} seconds ({duration/60:.2f} minutes)")
    else:
        print(f"Geçerli FPS veya frame sayısı alınamadı")

# Test et
test_video_duration('uploads/gurcukapi/videoplayback.mp4')
