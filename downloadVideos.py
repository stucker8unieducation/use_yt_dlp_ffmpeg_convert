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

def get_ffmpeg_path():
    """
    システムからFFmpegの実行ファイルのパスを検出する
    
    Returns:
        str or None: FFmpegのパス。見つからない場合はNone
    """
    try:
        # OSに応じてコマンドを選択
        if os.name == 'nt':  # Windows環境
            result = subprocess.run(['where', 'ffmpeg'], capture_output=True, text=True)
        else:  # Unix/Mac環境
            result = subprocess.run(['which', 'ffmpeg'], capture_output=True, text=True)
        
        if result.returncode == 0:
            return result.stdout.strip().split('\n')[0]
    except:
        # 一般的なインストール場所を順番にチェック
        common_paths = [
            '/usr/bin/ffmpeg',
            '/usr/local/bin/ffmpeg',
            '/opt/homebrew/bin/ffmpeg',  # Homebrew (Apple Silicon)
            '/opt/local/bin/ffmpeg'      # MacPorts
        ]
        for path in common_paths:
            if os.path.exists(path):
                return path
    return None

# 出力先ディレクトリの設定
CURRENT_HOME = str(Path.home())
VIDEO_FILE_PATH = os.path.join(CURRENT_HOME, 'Videos', 'MusicVideos')  # 動画の保存先
AUDIO_FILE_PATH = os.path.join(CURRENT_HOME, 'Music', 'Downloaded')    # 音声の保存先

# 必要なディレクトリを自動作成
os.makedirs(VIDEO_FILE_PATH, exist_ok=True)
os.makedirs(AUDIO_FILE_PATH, exist_ok=True)

def get_video_quality_settings(format_info):
    """
    動画の品質設定を取得する関数
    
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

def check_gpu_support():
    """
    GPUのサポート状況を確認
    
    Returns:
        bool: GPUエンコードが利用可能な場合はTrue
    """
    try:
        # FFmpegの各種情報を取得
        version_result = subprocess.run(
            [get_ffmpeg_path(), '-version'],
            capture_output=True,
            text=True
        )
        encoders_result = subprocess.run(
            [get_ffmpeg_path(), '-encoders'],
            capture_output=True,
            text=True
        )
        hwaccels_result = subprocess.run(
            [get_ffmpeg_path(), '-hwaccels'],
            capture_output=True,
            text=True
        )
        
        # OSに応じてGPUサポートをチェック
        if os.name == 'nt':  # Windows環境
            has_nvenc = 'h264_nvenc' in encoders_result.stdout
            has_cuda = 'cuda' in hwaccels_result.stdout
            if has_nvenc and has_cuda:
                print("\nGPUエンコード機能:")
                print(f"- NVIDIA NVENC: {'利用可能' if has_nvenc else '利用不可'}")
                print(f"- CUDA: {'利用可能' if has_cuda else '利用不可'}")
                return True
        else:  # macOS環境
            has_videotoolbox = 'videotoolbox' in hwaccels_result.stdout
            has_h264_videotoolbox = 'h264_videotoolbox' in encoders_result.stdout
            if has_videotoolbox and has_h264_videotoolbox:
                print("\nGPUエンコード機能:")
                print(f"- VideoToolbox: {'利用可能' if has_videotoolbox else '利用不可'}")
                print(f"- H.264 VideoToolbox: {'利用可能' if has_h264_videotoolbox else '利用不可'}")
                return True
        return False
    except:
        return False

def download_video(url, output_path='downloads', download_type='both', video_format='mp4'):
    """
    YouTubeから動画や音声をダウンロードする関数
    
    Args:
        url (str): YouTubeのURL
        output_path (str): 保存先ディレクトリ
        download_type (str): ダウンロードの種類（'video', 'audio', 'both'）
        video_format (str): 動画フォーマット（'mp4', 'webm', 'mkv', 'mov'）
        
    Returns:
        bool: 成功した場合はTrue、失敗した場合はFalse
    """
    # FFmpegの存在確認
    ffmpeg_path = get_ffmpeg_path()
    if not ffmpeg_path:
        print("エラー: FFmpegが見つかりません。")
        return False
    
    # フォーマット設定の定義
    format_settings = {
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
    
    # yt-dlpの基本設定
    ydl_opts = {
        'outtmpl': f'{output_path}/%(title)s.%(ext)s',  # タイトルをファイル名として使用
        'prefer_ffmpeg': True,
        'ffmpeg_location': ffmpeg_path,
        'restrictfilenames': False,  # ファイル名の制限を解除
        'verbose': True,
        'postprocessor_args': [
            '-loglevel', 'debug',
            '-stats',
        ],
    }
    
    try:
        # 動画情報の取得
        with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
            info = ydl.extract_info(url, download=False)
            
        if download_type == 'audio':
            print("\n音声をダウンロードします...")
            ydl_opts.update({
                'format': 'bestaudio/best',  # 最高品質の音声を選択
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'm4a',  # m4a形式で出力
                    'preferredquality': '0',  # 最高品質
                }],
                'postprocessor_args': [
                    '-c:a', 'aac',  # AACコーデックを使用
                    '-b:a', '0',    # 元のビットレートを保持
                    '-vn',          # ビデオストリームを無効化
                    '-y',           # 既存ファイルを上書き
                    '-loglevel', 'error'  # エラーログのみ表示
                ],
                'keepvideo': False,  # 元の動画ファイルを削除
                'writethumbnail': False,  # サムネイルをダウンロード
                'verbose': False,  # 詳細なログを無効化
                'embed_metadata': True,  # メタデータを埋め込む
                'embed_thumbnail': True,  # サムネイルを埋め込む
                'add_metadata': True  # メタデータを追加
            })
        
        elif download_type in ['video', 'both']:
            print(f"\n動画をダウンロードします（{video_format.upper()}形式）...")
            format_config = format_settings.get(video_format, format_settings['mp4'])
            ydl_opts.update({
                'format': format_config['format'],
                'merge_output_format': format_config['merge_output_format'],
                'postprocessors': [{
                    'key': 'FFmpegVideoConvertor',
                    'preferedformat': format_config['merge_output_format'],
                }],
                'postprocessor_args': format_config['postprocessor_args']
            })
        
        # ダウンロードの実行
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(url, download=True)
                print(f"\nダウンロードが完了しました: {info['title']}")
                return True
            except yt_dlp.DownloadError as e:
                print(f"\nダウンロード中にエラーが発生しました: {str(e)}")
                print(f"エラーの詳細: {type(e).__name__}")
                if hasattr(e, 'exc_info'):
                    print(f"例外情報: {e.exc_info}")
                return False
            
    except Exception as e:
        print(f"\n予期せぬエラーが発生しました: {str(e)}")
        print(f"エラーの詳細: {type(e).__name__}")
        if hasattr(e, '__traceback__'):
            import traceback
            print("トレースバック:")
            traceback.print_tb(e.__traceback__)
        return False

# メインプログラム
if __name__ == "__main__":
    print(f"動画の保存先: {VIDEO_FILE_PATH}")
    print(f"音声の保存先: {AUDIO_FILE_PATH}")
    
    # FFmpegとGPUサポートの確認
    ffmpeg_path = get_ffmpeg_path()
    if ffmpeg_path:
        print(f"FFmpegが見つかりました: {ffmpeg_path}")
        if check_gpu_support():
            print("GPUエンコードを使用します")
        else:
            print("警告: GPUエンコードが利用できません。CPUエンコードを使用します。")
    else:
        print("警告: FFmpegが見つかりません。以下のコマンドでインストールしてください:")
        print("brew install ffmpeg")
    
    # メインループ
    while True:
        # URLの入力受付
        url = input("\nYouTube URLを入力してください（終了するにはEnterキーのみ押してください）: ")
        if not url.strip():
            break
        
        # ダウンロード種類の選択
        print("\n1. 音声のみダウンロード（最高品質opus）")
        print("2. 動画のみダウンロード")
        print("3. 両方ダウンロード")
        choice = input("選択してください (1/2/3): ")
        
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
        
        # 選択に応じてダウンロード実行
        if choice == '1':
            download_video(url, AUDIO_FILE_PATH, 'audio')
        elif choice == '2':
            download_video(url, VIDEO_FILE_PATH, 'video', video_format)
        elif choice == '3':
            download_video(url, VIDEO_FILE_PATH, 'both', video_format)
        else:
            print("無効な選択です。")
        
        print("\n-----------------------------------")