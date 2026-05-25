# ビルド済みEXEの配布

Booth



# Lip Camera IP Server

Windows 上で対応するリップカメラ系デバイスのカメラ映像を取得し、ローカルプレビューおよび MJPEG HTTP ストリームとして配信する非公式の個人制作アプリケーションです。

ビルド後の実行ファイル名は `Lip_Camera_IP_Server.exe` です。アプリ画面のタイトルは `Lip Camera IP Server` です。

## 重要事項・利用規約

本ソフトウェアをダウンロード、起動、使用、複製または配布した場合、利用者は以下の条件に同意したものとみなされます。

1. 本ソフトウェアは個人のプロジェクトとして作成された非公式ソフトウェアです。デバイス製造元、プラットフォーム提供元、その他の関連会社によって開発、提供、承認、サポートまたは推奨されたものではなく、これらのサービス・製品・事業とは一切関係ありません。
2. 本ソフトウェアは利用者自身の判断と責任で使用してください。本ソフトウェアは無保証で提供され、作者は動作、適合性、安全性、安定性、正確性、継続的な利用可能性を保証しません。
3. 使用する PC、Windows、ドライバー、HMD、Lip Tracker、USB 構成、ネットワーク構成、ファームウェア等によって動作結果は異なります。すべての環境で正常に動作する保証はありません。
4. Windows、ドライバー、ファームウェア、プラットフォームその他の公式または第三者アップデート、仕様変更、セキュリティ変更等により、将来、本ソフトウェアの一部または全部が利用不能になる可能性があります。
5. 本ソフトウェアはカメラデバイスの制御、ストリームの有効化、赤外線 LED に関係する制御、およびネットワーク上への映像配信を行います。利用者は、使用前に周囲の安全、機器の状態、発熱、装着状態、ケーブル、プライバシーおよびネットワーク公開範囲を確認してください。
6. 適用法により認められる最大限の範囲で、本ソフトウェアの使用または使用不能に起因または関連して発生した、Lip Tracker、HMD、PC、周辺機器、身体、家財、データ、ネットワーク、プライバシーその他一切の損害、故障、事故、負傷、損失または費用について、作者は責任を負いません。
7. 映像サーバーの待受 IPv4 初期値は `127.0.0.1` であり、初期状態では同じ PC からのみアクセスできます。利用者が LAN 用 IPv4 アドレス等を手動指定してサーバーを開始した場合、ネットワーク上の他端末から映像へアクセス可能になる場合があります。第三者への意図しない映像公開、ファイアウォール設定、LAN/Wi-Fi の安全性、URL の共有および利用場所における撮影・プライバシー遵守は、利用者自身の責任です。
8. 適用法上排除できない権利または責任については、その適用法が許容する範囲でのみ本条項が適用されます。

## 機能

- Windows DirectShow 経由でカメラデバイスを開く
- 対応カメラデバイスに対する拡張ユニット制御
- アプリ画面内でのモノクロ映像プレビュー
- 映像の縦向き変換および MJPEG ストリーミング
- 英語・中国語・韓国語・日本語の UI 表示切り替え
- 待受 IPv4 アドレスの指定（初期値はローカル接続専用の `127.0.0.1`）
- 手動入力した IPv4 アドレスを優先して使用
- ポート番号の指定
- アプリ起動時のサーバー自動開始設定
- 設定値および選択言語の `settings.json` への保存

## HTTP エンドポイント

サーバー開始後、画面に表示された URL をブラウザ等から開きます。初期値 `127.0.0.1` のまま使用する場合は、アプリを実行している同じ PC からのみアクセスできます。LAN 内の別端末からアクセスする場合は、待受 IPv4 にこの PC に割り当てられた LAN 用 IPv4 アドレスを手動入力してからサーバーを開始してください。

| パス | 内容 |
| --- | --- |
| `/` または `/index.html` | 映像表示用 HTML ページ |
| `/stream` | MJPEG ストリーム |
| `/snapshot.jpg` | 最新の JPEG 静止画 |
| `/health` | サーバー稼働確認 (`ok`) |

> [!IMPORTANT]
> `127.0.0.1` はループバックアドレスです。初期設定のままでは別の PC やスマートフォンから接続できません。外部端末から利用する場合は、利用者自身の責任で LAN 用 IPv4 の指定とネットワーク公開範囲を確認してください。

初期設定で同じ PC からアクセスする例:

```text
http://127.0.0.1:8080/stream
```

LAN 内の別端末からアクセスする例（待受 IPv4 に `192.168.1.10` を手動指定した場合）:

```text
http://192.168.1.10:8080/stream
```

## 使用環境

- Windows 10 / Windows 11（64-bit を推奨）
- 対応する HTC Lip Camera / 対応カメラデバイスおよび必要なドライバー
- Toga WinForms バックエンドが使用できる .NET 環境
- ビルド時のみ Python と PyInstaller が必要

配布された `exe` を使用する PC には、Python のインストールは不要です。ただし、デバイスドライバーや OS 側の実行要件は別途必要です。

## UI 言語切り替え

画面上部の `Langage` プルダウンから、次の表示言語を選択できます。

- `English`
- `中文`
- `한국어`
- `日本語`

プルダウン横のラベルは、選択言語にかかわらず `Langage` と表示されます。選択した言語は `settings.json` に保存され、次回起動時に復元されます。

## 使い方

1. `Lip_Camera_IP_Server.exe` を起動します。
2. `デバイス番号` に対象カメラの番号を入力します。初期値は `1` です。
3. `カメラ有効` をオンにしてデバイスを開きます。
4. 必要に応じて `プレビュー` を押し、アプリ内で映像を確認します。
5. `待受IPv4` を設定します。
   - 初期値は `127.0.0.1` です。この設定では同じ PC からのみ映像へアクセスできます。
   - LAN 内の別端末から接続する場合は、この PC に割り当てられた LAN 用 IPv4 アドレスを手動入力してください。
   - 手動入力した IPv4 アドレスは、サーバー開始時にそのまま優先して使用されます。
6. `ポート` を入力します。既定値は `8080` です。
7. `サーバー開始` を押します。
8. `映像URL` 欄に表示された URL を、使用するクライアント側から開きます。
9. 終了時は `サーバー停止`、必要に応じて `カメラ有効` をオフにしてからアプリを閉じます。

### 設定ファイル

設定は実行ファイルと同じフォルダに `settings.json` として保存されます。保存対象には、カメラ番号、カメラ有効状態、待受 IPv4、ポート番号、自動開始設定、選択言語が含まれます。

待受 IPv4 の初期値は `127.0.0.1` です。旧バージョンで保存された待受 IPv4 が `0.0.0.0` の場合、サーバー開始時に `127.0.0.1` へ移行されます。

`--onedir` ビルドの場合:

```text
dist\Lip_Camera_IP_Server\
├─ Lip_Camera_IP_Server.exe
├─ settings.json
└─ _internal\
```

`--onefile` ビルドの場合:

```text
dist\
├─ Lip_Camera_IP_Server.exe
└─ settings.json
```

`Program Files` のように通常ユーザーが書き込めない場所へ配置すると、設定保存に失敗する場合があります。書き込み可能なフォルダで使用してください。

## ソース構成

```text
LIP_CAMERA_IP_SERVER\
├─ src\
│  ├─ app.py
│  ├─ camera.py
│  ├─ camera_server.py
│  └─ tracker_control.py
├─ requirements-windows.txt
├─ LICENSE.txt
└─ README.md
```

| ファイル | 役割 |
| --- | --- |
| `src/app.py` | Toga GUI、設定、フレーム処理、サーバー操作 |
| `src/camera.py` | DirectShow によるカメラキャプチャ |
| `src/camera_server.py` | HTTP / MJPEG サーバー |
| `src/tracker_control.py` | 対応カメラデバイスの拡張ユニット制御 |

## ビルド方法

以下は VS Code のターミナルで、プロジェクト直下から実行する手順です。ターミナルが PowerShell の場合を示します。

### 1. 仮想環境の作成と有効化

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

### 2. 依存ライブラリのインストール

`requirements-windows.txt` を管理している場合:

```powershell
python -m pip install -r .\requirements-windows.txt
python -m pip install pyinstaller
```

直接インストールする場合:

```powershell
python -m pip install pyinstaller toga opencv-python numpy Pillow pygrabber comtypes
```

### 3. Python 実行での確認

```powershell
python .\src\app.py
```

カメラを使用する前に、まずウィンドウが正常に起動することを確認してください。

### 4. 推奨ビルド: フォルダ配布形式 (`--onedir`)

```powershell
python -m PyInstaller --noconfirm --clean --name "Lip_Camera_IP_Server" --windowed --onedir --paths ".\src" --collect-all toga --collect-all toga_winforms --collect-all cv2 --collect-all pygrabber --collect-all comtypes ".\src\app.py"
```

生成物:

```text
dist\Lip_Camera_IP_Server\Lip_Camera_IP_Server.exe
```

配布する場合は `dist\Lip_Camera_IP_Server\` フォルダ全体を配布してください。

### 5. 単一 exe 形式 (`--onefile`)

`--onedir` 版で動作確認した後に実行してください。

```powershell
python -m PyInstaller --noconfirm --clean --name "Lip_Camera_IP_Server" --windowed --onefile --paths ".\src" --collect-all toga --collect-all toga_winforms --collect-all cv2 --collect-all pygrabber --collect-all comtypes ".\src\app.py"
```

生成物:

```text
dist\Lip_Camera_IP_Server.exe
```

`--onefile` 版は起動時の展開処理により起動が遅くなり、障害調査も難しくなる場合があります。

### 6. 起動エラー調査用ビルド

```powershell
python -m PyInstaller --noconfirm --clean --name "Lip_Camera_IP_Server_Debug" --console --onedir --paths ".\src" --collect-all toga --collect-all toga_winforms --collect-all cv2 --collect-all pygrabber --collect-all comtypes ".\src\app.py"
.\dist\Lip_Camera_IP_Server_Debug\Lip_Camera_IP_Server_Debug.exe
```

## 依存ライブラリとライセンス

アプリケーションソースコードは MIT License で提供されます。

コードおよび現在のビルド手順から確認できる主な外部コンポーネントは次のとおりです。

| コンポーネント | 用途 | 主なライセンス |
| --- | --- | --- |
| Python / 標準ライブラリ | Python ランタイム、標準機能 | PSF License Version 2 等 |
| PyInstaller | exe 化、ブートローダー | GPL-2.0-or-later WITH Bootloader-exception / 一部 Apache-2.0 |
| Toga / toga-core / toga-winforms / Travertino | GUI | BSD-3-Clause |
| Python.NET / clr-loader | Toga WinForms の .NET 連携に含まれ得る依存 | MIT |
| NumPy | フレーム配列処理 | BSD-3-Clause |
| OpenCV / opencv-python | 画像処理・JPEG エンコード | OpenCV: Apache-2.0、Python パッケージ: MIT |
| Pillow | GUI 用画像オブジェクト | MIT-CMU |
| pygrabber | DirectShow カメラ制御 | MIT |
| comtypes | Windows COM / 拡張ユニット連携 | MIT |

ライセンス本文と通知は `LICENSE-THIRD-PARTY.txt` に収録しています。

### リリース前のライセンス確認

`opencv-python`、`numpy`、`Pillow` 等の Windows wheel には、バージョンやビルド条件によってネイティブライブラリの追加ライセンス通知が含まれる場合があります。また、Toga や PyInstaller の依存パッケージ集合はインストールしたバージョンにより変化します。

そのため、配布直前に、実際にビルドに使う `.venv` 上で次を実行し、生成された結果と各パッケージ付属の `LICENSE*` / `NOTICE*` を配布物のライセンス通知へ追加してください。

```powershell
python -m pip freeze > .\requirements-windows-lock.txt
python -m pip install pip-licenses
python -m piplicenses --format=plain-vertical --with-license-file --with-notice-file --output-file ".\LICENSES-FROM-BUILD-ENV.txt"
Get-ChildItem .\.venv\Lib\site-packages -Recurse -File -Include "LICENSE*","NOTICE*","COPYING*" | Select-Object -ExpandProperty FullName
```

特に `opencv-python` が同梱する `LICENSE-3RD-PARTY.txt` は、FFmpeg その他のバイナリに関する通知を含むため、実際に配布するバージョンのファイルを必ず同梱してください。

## 商標等

HTC、VIVE その他本 README に記載される第三者の製品名、サービス名および商標は、それぞれの権利者に帰属します。本ソフトウェアおよび作者は、これらの権利を所有するものではありません。

本 README における名称の使用は、対応対象となり得る機器または動作環境を説明するためのものであり、各権利者との提携、後援、承認、公式対応または公式性を示すものではありません。

## ライセンス

本アプリケーションのソースコードは MIT License で提供されます。第三者コンポーネントは、それぞれのライセンス条件に従います。配布時は、本ファイルと `LICENSE-THIRD-PARTY.txt` を実行ファイルまたは配布フォルダに同梱してください。
