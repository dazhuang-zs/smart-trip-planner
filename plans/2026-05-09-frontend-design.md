# Smart Trip Planner 前端设计稿

**版本**: 1.0
**日期**: 2026-05-09
**设计者**: Claude (AI辅助设计)
**状态**: 已完成初始实现

---

## 1. 设计理念

**主题**: 旅行探索 · 森林系温暖
**关键词**: 自然、温暖、探索、品质

---

## 2. 配色系统

| 用途 | 颜色 | Hex |
|------|------|-----|
| 主色（森林绿） | Deep Forest | `#2D5A27` |
| 背景（米白） | Warm White | `#F5F5F0` |
| 点缀（秋季金） | Autumn Gold | `#E8A849` |
| 文字（深棕） | Bark Brown | `#3D2914` |
| 浅文字 | Muted Brown | `#8B7355` |
| 边框 | Sage | `#C5D5B8` |
| 错误 | Terracotta | `#E74C3C` |

---

## 3. 字体系统

| 用途 | 字体 | 大小 |
|------|------|------|
| 标题 | Noto Serif SC | 28px / 24px / 20px |
| 正文 | Inter / Noto Sans SC | 16px / 14px |
| 按钮 | Noto Sans SC Medium | 15px |

**Google Fonts 引入**:
- `Noto Serif SC` (300-600)
- `Playfair Display` (400, 600, 700)

---

## 4. 布局结构

### 4.1 整体布局
```
┌─────────────────────────────────────────────────────────┐
│  Header (64px)                                        │
│  [Logo] Smart Trip Planner                            │
├────────────────────────────┬────────────────────────────┤
│  Input Panel (50%)        │  Result Panel (50%)    │
│  ┌────────────────────┐  │  ┌────────────────────┐ │
│  │ 目的地              │  │  │                    │ │
│  │ 请输入目的地...    │  │  │  行程卡片          │ │
│  └────────────────────┘  │  │                    │ │
│  ┌────────────────────┐  │  │                    │ │
│  │ 偏好               │  │  │                    │ │
│  │ 深度游/到此一游   │  │  └────────────────────┘ │
│  └────────────────────┘  │                      │
│  ┌────────────────────┐      │                      │
│  │ 生成行程          │      │                      │
│  └────────────────────┘      │                      │
└────────────────────────────┴────────────────────────────┘
```

### 4.2 响应式断点
- **桌面**: >= 1024px (双栏)
- **平板**: 768px - 1023px (双栏紧凑)
- **手机**: < 768px (单栏堆叠)

---

## 5. 组件规格

### 5.1 Header
- 高度: 64px
- 内边距: 0 32px
- 背景: 森林绿渐变 `#2D5A27` → `#3D6B37`
- Logo: 🧭 Emoji 或 SVG
- 标题: Noto Serif SC, 24px, 白色

### 5.2 TripInput (输入面板)
- 目的地 textarea: 3行，高度 120px
- 出行天数: 数字输入 1-30，默认 3
- 偏好选择: 深度游 / 到此一游 / 亲子游 / 穷游自由
- 提交按钮: 森林绿背景，金色文字，圆角 8px

### 5.3 TripResult (结果面板)
- 空状态: 居中提示"输入目的地开始规划"
- 加载态: 森林绿 Loading 动画 + "规划中..."文字
- 结果态: 行程卡片列表
  - 地点名 (Noto Serif SC, 18px)
  - 地址 (14px, 浅文字)
  - 描述 (15px, 两行)
  - 评分 (★ 星星)

### 5.4 ���画规格
- 页面加载: fadeIn 0.5s ease-out
- 卡片显示: stagger 0.1s delay each
- 按钮悬停: scale 1.02, 0.2s ease
- 加载动画: spin 1s linear infinite

---

## 6. API 对接

**端点**: `POST /api/v1/trip/generate`

**请求体**:
```json
{
  "destination": "北京",
  "days": 3,
  "preference": "深度游"
}
```

**响应体**:
```json
{
  "trip_id": "abc123",
  "destination": "北京",
  "days": 3,
  "preference": "深度游",
  "itineraries": [
    {
      "day": 1,
      "date": "2026-05-10",
      "places": [
        {
          "name": "故宫博物院",
          "address": "东城区景山前街4号",
          "description": "中国明清两代的皇家宫殿...",
          "score": 4.8,
          "duration": "3小时"
        }
      ]
    }
  ]
}
```

**超时**: 60秒

---

## 7. 技术栈

- **构建**: Vite 5.4.11
- **框架**: React 18.3.1
- **HTTP**: axios 1.7.0
- **样式**: CSS Modules / Plain CSS

---

## 8. 文件结构

```
frontend/
├── index.html              # 入口 HTML，引入字体
├── package.json            # NPM 配置
├── vite.config.js           # Vite 配置 + API 代理
└── src/
    ├── main.jsx             # React 入口
    ├── App.jsx              # 主组件
    ├── App.css              # 全局样式 + 设计系统
    ├── components/
    │   ├── Header.jsx        # 头部
    │   ├── TripInput.jsx    # 输入表单
    │   └── TripResult.jsx   # 结果展示
    └── services/
        └── api.js           # API 调用封装
```

---

## 9. 启动方式

```bash
# 1. 后端
cd backend
uvicorn app.main:app --reload --port 8000

# 2. 前端（新终端）
cd frontend
npm install
npm run dev
```

访问: http://localhost:5173

---

## 10. 待优化项

1. [ ] 添加更多行程卡片样式
2. [ ] 地图集成（腾讯地图 JS API GL）
3. [ ] 收藏/分享功能
4. [ ] 暗黑模式支持
5. [ ] PWA 支持
6. [ ] 单元测试

---

*设计稿版本: v1.0 | 2026-05-09*