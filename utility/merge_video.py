import os
import subprocess

# ==========================================
# 1. 합칠 오디오 파일 이름 지정
# ==========================================
video1 = r"G:\내 드라이브\2026-1\0810_1a.m4a"  # 실제 파일 이름으로 변경하세요
video2 = r"G:\내 드라이브\2026-1\0810_1b.m4a"
output_video = r"G:\내 드라이브\2026-1\0810_1.m4a"

# ==========================================
# 2. 사전 체크: 입력 파일 존재 여부
# ==========================================
for f in (video1, video2):
    if not os.path.exists(f):
        print(f"❌ 파일을 찾을 수 없습니다: {f}")
        raise SystemExit(1)

# ==========================================
# 3. ffmpeg가 읽을 수 있도록 텍스트 파일 생성 (utf-8 인코딩)
# ==========================================
list_file = "file_list.txt"
with open(list_file, "w", encoding="utf-8") as f:
    f.write(f"file '{video1}'\n")
    f.write(f"file '{video2}'\n")

print("오디오를 합치는 중입니다... (재인코딩이라 약간 시간이 걸릴 수 있음)")

# ==========================================
# 4. ffmpeg 명령어 실행
# ⚠️ 변경점: "-c copy" 대신 오디오를 재인코딩함.
#    concat demuxer + stream copy는 MP4/M4A 컨테이너에서
#    타임스탬프(seek 인덱스)가 깨져서, 중간 구간을 클릭하면
#    엉뚱한 파일 위치로 점프하는 문제가 생길 수 있음.
#    재인코딩하면 타임스탬프가 처음부터 새로 계산되어 이 문제가 해결됨.
#    오디오 재인코딩은 비디오와 달리 매우 빠르게 끝남.
# ==========================================
command = [
    "ffmpeg",
    "-f", "concat",
    "-safe", "0",
    "-i", list_file,
    "-c:a", "aac",
    "-b:a", "192k",
    "-y",
    output_video
]

# capture_output을 쓰지 않으면 ffmpeg의 진행률(진행 시간, 속도 등)이
# 터미널에 그대로 실시간 출력됨. ffmpeg는 진행 상황을 stderr로 출력하므로
# 별도 파이프 없이 subprocess가 부모 프로세스의 stderr/stdout을 그대로 씀.
result = subprocess.run(command)

if result.returncode == 0:
    print(f"✅ 성공적으로 합쳐졌습니다! 결과 파일: {output_video}")
else:
    print("❌ 에러가 발생했습니다. 위 ffmpeg 출력을 확인하세요.")

# ==========================================
# 5. 사용한 임시 텍스트 파일 삭제
# ==========================================
if os.path.exists(list_file):
    os.remove(list_file)