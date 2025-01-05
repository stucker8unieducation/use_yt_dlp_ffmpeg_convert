import yt_dlp
import argparse
import os

def download_video(url, output_dir, format=None, username=None, password=None):
    ydl_opts = {
        'outtmpl': os.path.join(output_dir, '%(title)s.%(ext)s'),
        'format': format,
        'username': username,
        'password': password,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        print("ダウンロード完了")
    except yt_dlp.DownloadError as e:
        print(f"ダウンロード中にエラーが発生しました: {e}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='動画をダウンロードするスクリプト')
    parser.add_argument('url', type=str, help='ダウンロードする動画のURL')
    parser.add_argument('-o', '--output_dir', type=str, default='./downloads', help='ダウンロード先のディレクトリ')
    parser.add_argument('-f', '--format', type=str, help='ダウンロードするフォーマットを指定(例: mp4, webm)。指定しない場合はyt-dlpが最適なものを選択')
    parser.add_argument('-u', '--username', type=str, help='ログインが必要な場合のユーザー名')
    parser.add_argument('-p', '--password', type=str, help='ログインが必要な場合のパスワード')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.output_dir):
      os.makedirs(args.output_dir)
    
    download_video(args.url, args.output_dir, args.format, args.username, args.password)