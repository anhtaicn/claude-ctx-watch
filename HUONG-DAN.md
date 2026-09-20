# Context Watch — hướng dẫn nhanh (tiếng Việt)

Bản tiếng Anh đầy đủ nằm ở [README.md](README.md). File này chỉ để bạn chạy được trong năm phút.

## Nó giải quyết chuyện gì

Claude Code chỉ báo context của **cửa sổ bạn đang gõ**, và chỉ khi bạn gõ `/context` để hỏi. Ba cửa
sổ còn lại thì im lặng cho tới lúc một trong số đó tự nén ngữ cảnh giữa chừng. Tổng mức đốt quota
của cả máy thì không có chỗ nào hiện.

Bộ này mở một terminal nhỏ cạnh chỗ làm việc, 5 giây làm mới một lần, mỗi phiên một dòng: tên phiên
đúng như tên tab, số token đang giữ, phần trăm cửa sổ ngữ cảnh, còn sống hay đã đóng. Dòng trên
cùng là tổng token đã đốt trên cả máy trong 5 giờ và 10 phút gần nhất.

## Cần gì

- Python 3.8 trở lên (`python --version` để kiểm tra).
- Claude Code đã chạy ít nhất một lần, tức là đã có thư mục `~/.claude/`
  (Windows: `C:\Users\<tên bạn>\.claude\`).

Không cần cài thư viện, không cần API key, không gọi mạng. Bộ này chỉ đọc file transcript mà Claude
Code vốn đã ghi sẵn trên ổ đĩa của bạn.

## Cài trong ba bước

**Bước 1.** Giải nén thư mục này ra chỗ nào cũng được, ví dụ `D:\claude-ctx-watch`.

**Bước 2.** Mở PowerShell tại thư mục vừa giải nén, xem trước nó sẽ đụng vào những gì:

```powershell
python install.py --dry-run
```

**Bước 3.** Nếu thấy hợp lý thì chạy thật:

```powershell
python install.py
```

Trình cài chép bốn file vào `~/.claude/`, sao lưu mọi file bị ghi đè kèm dấu thời gian, rồi thêm
hook và statusline vào `settings.json`. Nó không xóa gì, và nếu `statusLine` của bạn đang dùng lệnh
khác thì nó **không** giành chỗ — nó in ra dòng JSON để bạn tự dán.

Hook chỉ có hiệu lực từ **phiên sau**, không phải phiên đang mở.

## Chạy

```powershell
python $HOME\.claude\ctx-watch.py
```

Muốn có nút bấm thay vì gõ lệnh: gộp `vscode/settings-snippet.json` vào `settings.json` của VS Code
và `vscode/keybindings-snippet.json` vào `keybindings.json`. Sau đó bấm mũi tên cạnh dấu `+` trong
khung Terminal rồi chọn **Context Watch**, hoặc bấm `Ctrl+Alt+W`.

Vài tham số hay dùng:

| Tham số | Tác dụng |
|---|---|
| `--since=240` | Hiện cả phiên đã im lặng trong 240 phút (mặc định 30) |
| `--interval=10` | Làm mới 10 giây một lần thay vì 5 |
| `--once` | In một lần rồi thoát |
| `--no-color` | Bỏ màu, dùng cho terminal không đọc được mã màu ANSI |

## Đọc một dòng thế nào

```
> aeo-first-82                                           14m
  █████░░░░░░░░░░░░░░░░░   227.9k  23% ● live
```

Dấu `>` là cửa sổ bạn vừa gõ lệnh vào. `14m` là khoảng lặng từ lần ghi cuối. `227.9k` là số token
phiên đó đang giữ, `23%` là phần trăm cửa sổ ngữ cảnh của model. Xanh lá dưới 50%, vàng từ 50%, đỏ
từ 75%. `● live` là còn chạy, `● busy` là đang giữa lượt, `x closed` là đã đóng.

Thấy chữ `win?` màu đỏ nghĩa là model đó chưa có trong bảng kích thước cửa sổ nên phần trăm chỉ là
ước lượng trên mốc 200k — con số token thì luôn đúng. Sửa bằng cách thêm model vào `WINDOWS` trong
`ctx-watch.py`, hoặc đặt biến môi trường `CLAUDE_CTX_WINDOW` trước khi chạy.

## Gỡ ra

Xóa bốn file đã chép vào `~/.claude/`, rồi bỏ hai mục hook và mục `statusLine` khỏi `settings.json`.
Bản sao lưu `settings.json.bak-<thời gian>` do trình cài tạo vẫn nằm ngay cạnh.

## Giới hạn đã biết

- Tên phiên đọc từ `~/.claude/sessions/<pid>.json` — file này do bản desktop app ghi. Chạy thuần CLI
  có thể không có file đó; khi ấy mỗi dòng chỉ hiện tám ký tự đầu của session id và luôn báo
  `x closed` vì không có pid để kiểm tra.
- Đã chạy thật trên Windows 11 với desktop app và VS Code. Nhánh macOS và Linux có trong mã nguồn
  nhưng chưa được chạy thử.
- Token quy đổi ở dòng `burn` là **token tương đương đầu vào**, không phải tiền. Dùng để so giờ này
  với giờ khác, không dùng để xuất hóa đơn.
