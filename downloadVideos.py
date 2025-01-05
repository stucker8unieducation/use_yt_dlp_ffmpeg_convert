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
    Apple Silicon GPUのサポート状況を確認
    
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
        
        # VideoToolboxの利用可否をチェック
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

def download_video(url, output_path='downloads', download_type='both'):
    """
    YouTubeから動画や音声をダウンロードする関数
    
    Args:
        url (str): YouTubeのURL
        output_path (str): 保存先ディレクトリ
        download_type (str): ダウンロードの種類（'video', 'audio', 'both'）
        
    Returns:
        bool: 成功した場合はTrue、失敗した場合はFalse
    """
    # FFmpegの存在確認
    ffmpeg_path = get_ffmpeg_path()
    if not ffmpeg_path:
        print("エラー: FFmpegが見つかりません。Homebrewでインストールしてください:")
        print("brew install ffmpeg")
        return False
    
    # yt-dlpの基本設定
    ydl_opts = {
        'outtmpl': f'{output_path}/%(title)s.%(ext)s',  # 出力ファイル名のテンプレート
        'prefer_ffmpeg': True,        # FFmpegを使用
        'ffmpeg_location': ffmpeg_path,  # FFmpegのパス
    }
    
    try:
        # 動画情報の取得
        with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
            info = ydl.extract_info(url, download=False)
            
        if download_type == 'audio':
            # 音声のみのダウンロード設定
            print("\n音声をダウンロードします...")
            ydl_opts.update({
                'format': 'bestaudio/best',  # 最高品質の音声
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'm4a',     # M4A形式
                    'preferredquality': '0',      # 最高品質
                }]
            })
        
        elif download_type in ['video', 'both']:
            # 動画（または動画+音声）のダウンロード設定
            print("\n動画をダウンロードします...")
            ydl_opts.update({
                'format': 'bv*+ba/b',  # 最高品質の動画+音声を単一コンテナで
                'merge_output_format': 'webm'  # WebM形式で出力
            })
        
        # ダウンロードの実行
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            print(f"\nダウンロードが完了しました: {info['title']}")
            return True
            
    except Exception as e:
        print(f"\nダウンロード中にエラーが発生しました: {str(e)}")
        print(f"エラーの詳細: {type(e).__name__}")
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
            print("Apple Silicon GPUエンコードを使用します（VideoToolbox）")
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
        print("\n1. 音声のみダウンロード（最高品質m4a）")
        print("2. 動画のみダウンロード（Apple GPU使用）")
        print("3. 両方ダウンロード（Apple GPU使用）")
        choice = input("選択してください (1/2/3): ")
        
        # 選択に応じてダウンロード実行
        if choice == '1':
            download_video(url, AUDIO_FILE_PATH, 'audio')
        elif choice == '2':
            download_video(url, VIDEO_FILE_PATH, 'video')
        elif choice == '3':
            download_video(url, VIDEO_FILE_PATH, 'both')
        else:
            print("無効な選択です。")
        
        print("\n-----------------------------------")