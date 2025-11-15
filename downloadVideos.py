#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YouTubeダウンローダー

このスクリプトは、YouTubeなどの動画サイトから最高品質の動画・音声をダウンロードし、
Apple Silicon GPUやWindows環境のGPUを活用して高速にエンコードします。

主な機能：
- 動画のダウンロード（最高品質、GPUエンコード）
- 音声のみのダウンロード（m4a形式）
- 動画と音声の両方をダウンロード
- Apple Silicon GPU（VideoToolbox）やWindows NVENCによるハードウェアエンコード
- 自動品質設定（解像度に基づく最適なビットレート）
"""
# 出力先ディレクトリ
CURRENT_HOME = str(Path.home())
VIDEO_FILE_PATH = os.path.join(CURRENT_HOME, 'Videos', 'MusicVideos')  # 動画の保存先
AUDIO_FILE_PATH = os.path.join(CURRENT_HOME, 'Music', 'Downloaded')    # 音声の保存先

# 動画・音声フォーマット設定
FORMAT_SETTINGS = {
    'mp4': {
        'format': 'bestvideo[ext=mp4][dynamic_range=HDR]+bestaudio[ext=m4a]/bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'merge_output_format': 'mp4',
        'postprocessor_args': [
            '-c:v', 'copy',
            '-c:a', 'aac',
            '-movflags', '+use_metadata_tags',
            '-map_metadata', '0',
        ]
    },
    'webm': {
        'format': 'bestvideo[ext=webm][dynamic_range=HDR]+bestaudio[ext=webm]/bestvideo[ext=webm]+bestaudio[ext=webm]/best[ext=webm]/best',
        'merge_output_format': 'webm',
        'postprocessor_args': [
            '-c:v', 'copy',
            '-c:a', 'libvorbis',
        ]
    },
    'mkv': {
        'format': 'bestvideo[dynamic_range=HDR]+bestaudio/bestvideo+bestaudio/best',
        'merge_output_format': 'mkv',
        'postprocessor_args': [
            '-c:v', 'copy',
            '-c:a', 'copy',
        ]
    },
    'mov': {
        'format': 'bestvideo[ext=mp4][dynamic_range=HDR]+bestaudio[ext=m4a]/bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'merge_output_format': 'mov',
        'postprocessor_args': [
            '-c:v', 'copy',
            '-c:a', 'aac',
            '-movflags', '+use_metadata_tags',
            '-map_metadata', '0',
        ]
    }
}

def print_error(msg, exc=None):
    """
    エラーメッセージを統一的に出力
    """
    print(f"\n[エラー] {msg}")
    if exc:
        print(f"種類: {type(exc).__name__}")
        print(f"内容: {exc}")
        import traceback
        traceback.print_tb(exc.__traceback__)
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YouTubeダウンローダー

このスクリプトは、YouTubeから動画や音声をダウンロードし、
Apple Silicon GPUを使用して高速にエンコードします。

主な機能：
- 動画のダウンロード（最高品質、GPUエンコード）
- 音声のみのダウンロード（m4a形式）
- 動画と音声の両方をダウンロード
- Apple Silicon GPU（VideoToolbox）によるハードウェアエンコード
- 自動品質設定（解像度に基づく最適なビットレート）
"""

import yt_dlp
import os
import subprocess
from pathlib import Path

def detect_ffmpeg():
    """
    システムからFFmpegの実行ファイルのパスを検出
    Returns:
        str or None: FFmpegのパス。見つからない場合はNone
    """
    if os.name == 'nt':
        result = subprocess.run(['where', 'ffmpeg'], capture_output=True, text=True)
    else:
        result = subprocess.run(['which', 'ffmpeg'], capture_output=True, text=True)
    if result.returncode == 0:
        return result.stdout.strip().split('\n')[0]
    # 一般的なインストール場所を順番にチェック
    common_paths = [
        '/usr/bin/ffmpeg',
        '/usr/local/bin/ffmpeg',
        '/opt/homebrew/bin/ffmpeg',
        '/opt/local/bin/ffmpeg'
    ]
    for path in common_paths:
        if os.path.exists(path):
            return path
    return None


os.makedirs(VIDEO_FILE_PATH, exist_ok=True)
os.makedirs(AUDIO_FILE_PATH, exist_ok=True)

def get_video_quality_settings(format_info):
    """
    動画の品質設定（FFmpegオプション）を取得
    Args:
        format_info (dict): 動画フォーマット情報
    Returns:
        list: FFmpegのエンコード設定オプション
    """
    # ビットレートの取得または推定（kbps）
    vbr = format_info.get('vbr', 0) or format_info.get('tbr', 0)
    if not vbr:
        # ビットレートが不明な場合は解像度から最適な値を推定
        height = format_info.get('height', 0)
        if height >= 2160:      # 4K
            vbr = 45000         # 45Mbps
        elif height >= 1440:    # 2K
            vbr = 25000         # 25Mbps
        elif height >= 1080:    # Full HD
            vbr = 8000          # 8Mbps
        elif height >= 720:     # HD
            vbr = 5000          # 5Mbps
        else:                   # SD
            vbr = 2500          # 2.5Mbps
    
    # ビットレートをbps単位に変換
    bitrate = str(int(vbr * 1000))
    
    # Apple Silicon GPU用の最適化された設定
    return [
        # 入力オプション（デコード設定）
        '-hwaccel', 'videotoolbox',          # VideoToolboxでハードウェアデコード
        '-hwaccel_output_format', 'videotoolbox_vld',  # GPUメモリを使用
        
        # 出力オプション（エンコード設定）
        '-c:v', 'h264_videotoolbox',         # VideoToolboxでH.264エンコード
        '-b:v', bitrate,                     # 動画ビットレート
        '-allow_sw', '0',                    # ハードウェアエンコードを強制
        '-profile:v', 'high',                # H.264 Highプロファイル（高品質）
        '-level', '4.2',                     # H.264レベル（互換性）
        '-q:v', '35',                        # 品質設定（0-100、低いほど高品質）
        '-pix_fmt', 'nv12',                  # VideoToolbox最適化ピクセルフォーマット
        
        # 音声設定
        '-c:a', 'aac',                       # AACコーデック
        '-b:a', '320k',                      # 音声ビットレート（320kbps）
        
        # その他の設定
        '-movflags', '+faststart'            # Web再生用の最適化
    ]

def check_gpu_support(ffmpeg_path):
    """
    GPUエンコードのサポート状況を確認
    Args:
        ffmpeg_path (str): FFmpegのパス
    Returns:
        bool: GPUエンコードが利用可能な場合はTrue
    """
    try:
        version_result = subprocess.run([ffmpeg_path, '-version'], capture_output=True, text=True)
        encoders_result = subprocess.run([ffmpeg_path, '-encoders'], capture_output=True, text=True)
        hwaccels_result = subprocess.run([ffmpeg_path, '-hwaccels'], capture_output=True, text=True)
        if os.name == 'nt':
            has_nvenc = 'h264_nvenc' in encoders_result.stdout
            has_cuda = 'cuda' in hwaccels_result.stdout
            if has_nvenc and has_cuda:
                print("\nGPUエンコード機能:")
                print(f"- NVIDIA NVENC: {'利用可能' if has_nvenc else '利用不可'}")
                print(f"- CUDA: {'利用可能' if has_cuda else '利用不可'}")
                return True
        else:
            has_videotoolbox = 'videotoolbox' in hwaccels_result.stdout
            has_h264_videotoolbox = 'h264_videotoolbox' in encoders_result.stdout
            if has_videotoolbox and has_h264_videotoolbox:
                print("\nGPUエンコード機能:")
                print(f"- VideoToolbox: {'利用可能' if has_videotoolbox else '利用不可'}")
                print(f"- H.264 VideoToolbox: {'利用可能' if has_h264_videotoolbox else '利用不可'}")
                return True
        return False
    except Exception as e:
        print_error("GPUサポート判定中に例外が発生しました。", e)
        return False


def download_video(url, output_path, download_type, video_format='mp4', ffmpeg_path=None):
    """
    動画・音声ダウンロード処理
    Args:
        url (str): 動画URL
        output_path (str): 保存先
        download_type (str): 'video', 'audio', 'both'
        video_format (str): 'mp4', 'webm', 'mkv', 'mov'
        ffmpeg_path (str): FFmpegのパス
    Returns:
        bool: 成功時True
    """
    if not ffmpeg_path:
        ffmpeg_path = detect_ffmpeg()
    if not ffmpeg_path:
        print_error("FFmpegが見つかりません。")
        return False
    format_config = FORMAT_SETTINGS.get(video_format, FORMAT_SETTINGS['mp4'])
    ydl_opts = {
        'outtmpl': f'{output_path}/%(title)s.%(ext)s',
        'prefer_ffmpeg': True,
        'ffmpeg_location': ffmpeg_path,
        'restrictfilenames': False,
        'verbose': True,
        'postprocessor_args': [
            '-loglevel', 'debug',
            '-stats',
        ],
        'extractor_args': {
            'generic': ['impersonate=chrome']
        }
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
        if download_type == 'audio':
            print("\n音声をダウンロードします...")
            ydl_opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'm4a',
                    'preferredquality': '0',
                }],
                'postprocessor_args': [
                    '-c:a', 'aac',
                    '-b:a', '0',
                    '-vn',
                    '-y',
                    '-loglevel', 'error'
                ],
                'keepvideo': False,
                'writethumbnail': False,
                'verbose': False,
                'embed_metadata': True,
                'embed_thumbnail': True,
                'add_metadata': True
            })
        elif download_type in ['video', 'both']:
            print(f"\n動画をダウンロードします（{video_format.upper()}形式）...")
            ydl_opts.update({
                'format': format_config['format'],
                'merge_output_format': format_config['merge_output_format'],
                'postprocessors': [{
                    'key': 'FFmpegVideoConvertor',
                    'preferedformat': format_config['merge_output_format'],
                }],
                'postprocessor_args': format_config['postprocessor_args']
            })
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(url, download=True)
                print(f"\nダウンロードが完了しました: {info['title']}")
                return True
            except yt_dlp.DownloadError as e:
                print_error("ダウンロード中にエラーが発生しました。", e)
                if hasattr(e, 'exc_info'):
                    print(f"例外情報: {e.exc_info}")
                return False
    except Exception as e:
        print_error("予期せぬエラーが発生しました。", e)
        return False


def cli_main():
    """
    CLI処理のメイン関数
    """
    print(f"動画の保存先: {VIDEO_FILE_PATH}")
    print(f"音声の保存先: {AUDIO_FILE_PATH}")
    ffmpeg_path = detect_ffmpeg()
    if ffmpeg_path:
        print(f"FFmpegが見つかりました: {ffmpeg_path}")
        if check_gpu_support(ffmpeg_path):
            print("GPUエンコードを使用します")
        else:
            print("警告: GPUエンコードが利用できません。CPUエンコードを使用します。")
    else:
        print("警告: FFmpegが見つかりません。以下のコマンドでインストールしてください:")
        print("brew install ffmpeg")
    while True:
        url = input("\nYouTube URLを入力してください（終了するにはEnterキーのみ押してください）: ")
        if not url.strip():
            break
        print("\n1. 音声のみダウンロード（最高品質opus）")
        print("2. 動画のみダウンロード")
        print("3. 両方ダウンロード")
        choice = input("選択してください (1/2/3): ")
        video_format = 'mp4'
        if choice in ['2', '3']:
            print("\n動画フォーマットを選択してください:")
            print("1. MP4 (推奨、最も互換性が高い)")
            print("2. WebM")
            print("3. MKV (最高品質、柔軟性が高い)")
            print("4. MOV (Appleデバイス向け)")
            format_choice = input("選択してください (1/2/3/4): ")
            format_map = {
                '1': 'mp4',
                '2': 'webm',
                '3': 'mkv',
                '4': 'mov'
            }
            video_format = format_map.get(format_choice, 'mp4')
        if choice == '1':
            download_video(url, AUDIO_FILE_PATH, 'audio', ffmpeg_path=ffmpeg_path)
        elif choice == '2':
            download_video(url, VIDEO_FILE_PATH, 'video', video_format, ffmpeg_path=ffmpeg_path)
        elif choice == '3':
            download_video(url, VIDEO_FILE_PATH, 'both', video_format, ffmpeg_path=ffmpeg_path)
        else:
            print("無効な選択です。")
        print("\n-----------------------------------")


if __name__ == "__main__":
    cli_main()