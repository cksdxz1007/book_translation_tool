# 网站图标文件说明

## 文件列表

### ICO 格式 (推荐)
- `favicon.ico` - 多尺寸图标（16x16, 32x32, 48x48）
  - 用于浏览器标签页显示
  - 桌面快捷方式图标

### PNG 格式 (现代)
- `favicon-16x16.png` - 16x16px
- `favicon-32x32.png` - 32x32px
- `apple-touch-icon.png` - 180x180px (Apple 设备)
- `android-chrome-192x192.png` - 192x192px (Android)
- `android-chrome-512x512.png` - 512x512px (PWA)

## 如何使用

### 方法 1: 生成图标文件
1. 使用在线工具如 [favicon.io](https://favicon.io/) 或 [RealFaviconGenerator](https://realfavicongenerator.net/)
2. 上传您的图标设计（建议 512x512px）
3. 下载生成的 favicon 套件
4. 将文件复制到此目录

### 方法 2: 使用在线工具快速生成
访问以下网站，输入 "翻译" 或 "translation" 关键词，选择合适的图标：
- favicon.io
- icons8.com
- flaticon.com

## HTML 引用代码

在您的 HTML `<head>` 部分添加以下代码：

```html
<!-- ICO 格式（兼容性最好） -->
<link rel="icon" type="image/x-icon" href="/static/favicon/favicon.ico">

<!-- PNG 格式（现代浏览器） -->
<link rel="icon" type="image/png" sizes="16x16" href="/static/favicon/favicon-16x16.png">
<link rel="icon" type="image/png" sizes="32x32" href="/static/favicon/favicon-32x32.png">

<!-- Apple 设备 -->
<link rel="apple-touch-icon" sizes="180x180" href="/static/favicon/apple-touch-icon.png">

<!-- Android/Chrome -->
<link rel="icon" type="image/png" sizes="192x192" href="/static/favicon/android-chrome-192x192.png">
<link rel="icon" type="image/png" sizes="512x512" href="/static/favicon/android-chrome-512x512.png">

<!-- Web App Manifest -->
<link rel="manifest" href="/static/favicon/site.webmanifest">
```

## 快速设置

如果您需要快速设置 favicon，最简单的方法是：

1. 访问 [favicon.io](https://favicon.io/favicon-generator/)
2. 输入 "翻译工具" 或 "Translator"
3. 选择合适的图标样式
4. 下载生成的 favicon.ico 文件
5. 将文件放到 `/static/favicon/favicon.ico`
6. 在 HTML 模板中添加引用代码
