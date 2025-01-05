#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
動画フォーマット変換スクリプト

このスクリプトは、入力された動画ファイルをMOV形式に変換します。
変換時は可能な限り元の品質を維持し、必要に応じてCPUまたはGPUを使用して
高速なエンコードを行います。

主な機能：
- 動画ファイルのMOV形式への変換
- WebM形式からの変換に対応
- HDRコンテンツの適切な処理
- 高品質設定でのエンコード
- 中断時の一時ファイル自動削除
"""

import ffmpeg
import signal
import sys
from pathlib import Path

# グローバル変数で現在処理中のファイルを追跡
current_output_file = None

def cleanup_temp_file():
    """
    一時ファイルを削除する関数
    """
    global current_output_file
    if current_output_file and Path(current_output_file).exists():
        try:
            Path(current_output_file).unlink()
            print(f"\n一時ファイルを削除しました: {current_output_file}")
        except Exception as e:
            print(f"一時ファイルの削除中にエラーが発生しました: {e}")

def signal_handler(signum, frame):
    """
    シグナルハンドラー関数
    Ctrl+Cなどのシグナルをキャッチしてクリーンアップを実行
    """
    print("\n処理を中断します...")
    cleanup_temp_file()
    sys.exit(1)

def get_video_info(input_path):
    """
    入力動画の情報を取得
    
    Args:
        input_path (str): 入力動画ファイルのパス
        
    Returns:
        dict: 動画情報（コーデック、解像度など）
    """
    probe = ffmpeg.probe(str(input_path))
    video_info = next(s for s in probe['streams'] if s['codec_type'] == 'video')
    return video_info

def convert_to_mov(input_path, output_dir=None, preset='veryslow', audio_codec='aac'):
    """
    動画ファイルをMOV形式に変換する関数
    
    変換時は以下の優先順位で処理を行います：
    1. HEVC (H.265) VideoToolboxでGPUエンコード
    2. 失敗時はlibx265でCPUエンコード
    3. 入力がProResの場合：コーデックを直接コピー
    
    品質維持の方針：
    - HDR情報やカラースペース情報を保持
    - オリジナルの解像度とフレームレートを維持
    
    Args:
        input_path (str): 入力動画ファイルのパス
        output_dir (str, optional): 出力ディレクトリ。指定がない場合は入力ファイルと同じディレクトリを使用
        preset (str, optional): エンコードプリセット（veryslow, slower, slow, medium, fast, faster, veryfast）
        audio_codec (str, optional): 音声コーデック（aac, copy, mp3, opus）
    
    Returns:
        str: 出力されたMOVファイルのパス
    """
    global current_output_file
    
    try:
        input_path = Path(input_path)
        output_dir = Path(output_dir) if output_dir else input_path.parent
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{input_path.stem}.mov"
        
        # 出力ファイルパスを記録（クリーンアップ用）
        current_output_file = str(output_path)
        
        # 既存の出力ファイルがある場合は削除
        if output_path.exists():
            output_path.unlink()
        
        # 入力ファイルの情報を取得
        probe = ffmpeg.probe(str(input_path))
        video_info = next(s for s in probe['streams'] if s['codec_type'] == 'video')
        
        # 解像度の取得
        width = int(video_info.get('width', 1920))
        height = int(video_info.get('height', 1080))
        fps = float(eval(video_info.get('r_frame_rate', '30/1')))
        
        # HDR/カラースペース情報の確認
        is_hdr = False
        color_space = video_info.get('color_space', '')
        color_transfer = video_info.get('color_transfer', '')
        color_primaries = video_info.get('color_primaries', '')
        
        if 'side_data_list' in video_info:
            for side_data in video_info['side_data_list']:
                if side_data.get('side_data_type') == 'Content light level metadata':
                    is_hdr = True
                    break
        
        if is_hdr:
            print("HDRコンテンツを検出しました")
        
        # 解像度の確認と出力
        if height >= 8640 or width >= 15360:
            print("12K解像度を検出しました")
        elif height >= 4320 or width >= 7680:
            print("8K解像度を検出しました")
        elif height >= 2160 or width >= 3840:
            print("4K解像度を検出しました")

        # 入力設定
        stream = ffmpeg.input(str(input_path))

        if video_info['codec_name'] == 'prores':
            print("ProResコーデックを直接コピーします")
            print(f"音声コーデック: {audio_codec}")
            stream = ffmpeg.output(stream, str(output_path),
                                 vcodec='copy',
                                 acodec=audio_codec,
                                 audio_bitrate='320k' if audio_codec != 'copy' else None,
                                 format='mov')
        else:
            print("VideoToolbox (GPU)を使用してHEVC (H.265)で変換を試みます")
            
            # ビットレートの計算
            base_bitrate = 100 if height >= 2160 else 50 if height >= 1440 else 20 if height >= 1080 else 10
            bitrate = base_bitrate * (min(fps, 60) / 30)
            maxrate = int(bitrate * 1.5)
            bufsize = int(bitrate * 2)
            
            print(f"出力設定: {width}x{height}, FPS: {fps}")
            print(f"ビットレート: {bitrate}M (最大: {maxrate}M)")
            print(f"音声コーデック: {audio_codec}")
            
            # 出力設定
            output_args = {
                'vcodec': 'hevc_videotoolbox',  # HEVCエンコーダー
                'video_bitrate': f"{bitrate}M",
                'maxrate': f"{maxrate}M",
                'bufsize': f"{bufsize}M",
                'profile:v': 'main',
                'pix_fmt': 'nv12',
                'acodec': audio_codec,
                'ar': '48000',                  # サンプリングレート
                'audio_bitrate': '320k' if audio_codec != 'copy' else None,
                'movflags': '+faststart',
                'tag:v': 'hvc1',                # HEVCタグ
                'format': 'mov'
            }
            
            # None値を持つキーを削除
            output_args = {k: v for k, v in output_args.items() if v is not None}
            
            stream = ffmpeg.output(stream, str(output_path), **output_args)
        
        stream = ffmpeg.overwrite_output(stream)
        
        try:
            print(f"\n変換開始: {input_path.name} → {output_path.name}")
            process = ffmpeg.run(stream, capture_stdout=True, capture_stderr=True)
            print(f"完了: {output_path}")
            return str(output_path)
        except ffmpeg.Error as e:
            # VideoToolboxのエンコードに失敗した場合は、
            # エラーログを見て対応をする
            err_msg = e.stderr.decode()
            print(f"VideoToolboxエンコード失敗:\n{err_msg}")
            
            if "Error: cannot create compression session: -12903" in err_msg or \
               "Error while opening encoder" in err_msg or \
               "hardware encoder may be busy, or not supported" in err_msg:
                print("VideoToolboxが失敗したため、libx265で再試行します。")
                
                # VideoToolboxが失敗した場合のlibx265設定
                output_args = {
                    'vcodec': 'libx265',           # H.265 CPUエンコーダー
                    'crf': 23,                     # HEVC用の品質基準値
                    'preset': preset,              # エンコード速度と品質のバランス
                    'profile:v': 'main10',         # HEVC 10bitプロファイル
                    'pix_fmt': 'yuv420p10le' if is_hdr else 'yuv420p',  # HDR対応10bit
                    'x265-params': f"aq-mode=3:no-fast-pskip=1:deblock=-1,-1",  # 高品質設定
                    'acodec': audio_codec,         # 音声コーデック
                    'ar': '48000',                 # サンプリングレート
                    'audio_bitrate': '320k' if audio_codec != 'copy' else None,  # 音声ビットレート
                    'movflags': '+faststart',      # Web再生用の最適化
                    'tag:v': 'hvc1',               # HEVCタグ
                    'format': 'mov',               # 出力フォーマット
                    'threads': 'auto'              # 自動スレッド数設定
                }
                
                # HDR/カラースペース情報の保持
                if is_hdr and color_space and color_transfer and color_primaries:
                    # x265-paramsにHDR設定を追加
                    x264_params = [
                        "aq-mode=3",
                        "no-fast-pskip=1",
                        "deblock=-1,-1",
                        f"colorprim={color_primaries}",
                        f"transfer={color_transfer}",
                        f"colormatrix={color_space}"
                    ]
                    output_args['x265-params'] = ":".join(x264_params)
                
                # None値を持つキーを削除
                output_args = {k: v for k, v in output_args.items() if v is not None}
                
                stream = ffmpeg.output(stream, str(output_path), **output_args)
                
                try:
                    print(f"\nlibx265による最高品質変換開始: {input_path.name} → {output_path.name}")
                    process = ffmpeg.run(stream, capture_stdout=True, capture_stderr=True)
                    print(f"完了: {output_path}")
                    return str(output_path)
                except ffmpeg.Error as e:
                    print(f"libx265エンコード失敗: {e.stderr.decode()}")
                    print("\nFFmpegコマンド:")
                    print(' '.join(ffmpeg.compile(stream)))
                    raise
            
            print("\nFFmpegコマンド:")
            print(' '.join(ffmpeg.compile(stream)))
            raise  # 処理できないffmpeg.Error を再送出
        
    except Exception as e:
        cleanup_temp_file()
        raise e
    
    return str(output_path)

# メイン処理
if __name__ == "__main__":
    import argparse
    
    # シグナルハンドラーの設定
    signal.signal(signal.SIGINT, signal_handler)   # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)  # 終了シグナル
    
    # コマンドライン引数の設定
    parser = argparse.ArgumentParser(description='動画をMOV形式に変換')
    parser.add_argument('input', help='入力ファイルのパス')
    parser.add_argument('--output-dir', help='出力ディレクトリ（省略可）')
    parser.add_argument('--preset', default='veryslow', 
                       choices=['veryslow', 'slower', 'slow', 'medium', 'fast', 'faster', 'veryfast'],
                       help='エンコードプリセット（品質と速度のバランス）')
    parser.add_argument('--audio-codec', default='aac',
                       choices=['aac', 'copy', 'mp3', 'opus'],
                       help='音声コーデック（aac, copy, mp3, opus）')
    
    # 引数の解析
    args = parser.parse_args()
    
    try:
        # 変換の実行と結果の表示
        output_path = convert_to_mov(args.input, args.output_dir, args.preset, args.audio_codec)
        print(f"\n保存先: {output_path}")
    except KeyboardInterrupt:
        print("\n処理が中断されました")
        cleanup_temp_file()
        sys.exit(1)
    except Exception as e:
        print(f"エラー: {str(e)}")
        cleanup_temp_file()
        sys.exit(1)
