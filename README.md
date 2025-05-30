# gemini_webapi_server

A FastAPI-based REST API server that provides OpenAI-compatible endpoints powered by Google Gemini through the `gemini_webapi` integration.




## 🚀 更优雅地手动获取 Gemini 凭证

> 适用于所有场景，特别是某些安全级别高的账号无法正常在无头浏览器中登录。


### 安装 Cookie Editor 插件

1. 打开浏览器扩展商店  
2. 搜索并安装 “Cookie Editor”  

- **Chrome**：  
  [chrome.google.com/webstore/detail/cookie-editor/hlkenndednhfkekhgcdicdfddnkalmdm](https://chrome.google.com/webstore/detail/cookie-editor/hlkenndednhfkekhgcdicdfddnkalmdm)  
- **Edge**：  
  [microsoftedge.microsoft.com/addons/detail/cookieeditor/neaplmfkghagebokkhpjpoebhdledlfi](https://microsoftedge.microsoft.com/addons/detail/cookieeditor/neaplmfkghagebokkhpjpoebhdledlfi)  
- **Firefox**：  
  [addons.mozilla.org/addon/cookie-editor](https://addons.mozilla.org/addon/cookie-editor)  
- **Safari**：  
  [apps.apple.com/app/apple-store/id6446215341](https://apps.apple.com/app/apple-store/id6446215341)  
- **Opera**：  
  [addons.opera.com/en/extensions/details/cookie-editor-2](https://addons.opera.com/en/extensions/details/cookie-editor-2)  

---

### 登录 Gemini

1. 打开浏览器，访问：https://gemini.google.com  
2. 使用你的 Google 账号完成登录流程。

---

### 提取 Cookie 值

1. 点击浏览器工具栏中的 **Cookie Editor** 插件图标  
2. 在搜索框中输入 `SECURE-1PSID`，复制其 **Value**  
3. 同理，搜索并复制 `SECURE-1PSIDTS` 的 **Value**

---

### 配置 `.env` 文件

将值更新至项目根目录下的 `.env` 文件

```dotenv
# Gemini 凭证
SECURE_1PSID={}
SECURE_1PSIDTS={}
````
