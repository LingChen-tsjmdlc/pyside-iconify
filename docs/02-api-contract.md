# 2. 接口设计

这页定义「怎么用」。Step 1 的离线能力与 Step 2 的联网下载、磁盘缓存均已实现。

**核心定位：产出标准 `QIcon`。** 所以主要接口是 `get_icon()`，不是控件。

## 2.1 最常见的用法

```python
from pyside_iconify import get_icon

button.setIcon(get_icon("mdi:home", size=24, color="red"))
```

`get_icon` 返回标准 `QIcon`，**能接 `QIcon` 的地方都能用**：

```python
action.setIcon(get_icon("mdi:save"))
tab_widget.setTabIcon(0, get_icon("mdi:file"))
tray.setIcon(get_icon("mdi:apps"))
tree_item.setIcon(0, get_icon("mdi:folder"))
my_custom_widget.setIcon(get_icon("mdi:home"))   # 你自己写的控件
```

**这里没有类型适配。** 库不需要知道目标是什么，也不需要为每种控件写支持代码。

### 数据还没到也能先用

返回的 `QIcon` 里装的是我们自己的绘制引擎，**每次要画时才取当前数据**：

- 数据没到 → 先调用 `mark_pending("prefix:name")`，图标画透明空白
- 数据到了 → 后台线程或主线程调用 `add_icon()` / `add_collection()` 注册数据，`IconWidget` 自动刷新

所以不必先等加载、也不必手动重设一次。

`mark_pending()` 只标记“数据正在加载”，不会联网。Step 2 的网络层会用它；离线程序也可在后台解析 JSON 前先标记。确认图标不存在时不要调用它，直接让库显示缺失占位图。

如果用 `add_icon()` 注册一段原始 SVG body，而路径坐标不是默认的 16×16，请传完整 `IconData(body, width, height)`，例如 `IconData(body, 24, 24)`。Iconify JSON 自带宽高，不需要额外指定。用 `replace=True` 替换已有图标时，库会保留已有图标的坐标系。

**这条依赖 Qt 的重绘行为，Step 1 会真机验证。** 如果 Qt 因内部缓存不刷新，我会说明并给替代方案。

### 需要独立控件时用 IconWidget

```python
from pyside_iconify import IconWidget

layout.addWidget(IconWidget("mdi:home", size=24))
```

`IconWidget` 是普通 `QWidget`，能进布局、能设样式表、能当子控件。适合：单独显示一个图标、需要 `loaded` / `failed` 信号、需要精确控制刷新时机。

### 不接受 QIcon 的目标

比如 `QLabel` 只收 `QPixmap`：

```python
label.setPixmap(get_pixmap("mdi:home", size=24))
```

`get_pixmap` 返回的是静态图，**不会自动刷新**。想要自动刷新就用 `IconWidget`。

## 2.2 参数

`get_icon` 和 `IconWidget` 的显示参数一致：

```py
get_icon(图标名, *, size=24, color=None, color_light_theme=None, color_dark_theme=None,
         selected_color=None, selected_color_light_theme=None, selected_color_dark_theme=None,
         opacity=1.0, width=None, height=None, rotate=0, spin=False,
         h_flip=False, v_flip=False)

IconWidget(图标名, *, size=24, color=None, color_light_theme=None, color_dark_theme=None,
           hover_color=None, hover_color_light_theme=None, hover_color_dark_theme=None,
           opacity=1.0, width=None, height=None, rotate=0, spin=False,
           h_flip=False, v_flip=False, qss=None, parent=None)
```

`qss` 是 QSS 分组标签：内部写进 Qt 动态属性，不是 Web 风格的额外样式参数。

| 参数                                                       | 说明                                                                      |
| ---------------------------------------------------------- | ------------------------------------------------------------------------- |
| 图标名                                                     | `"mdi:home"`，或直接给图标数据                                            |
| `size`                                                     | 大小，默认 24，图形等比居中。可传数字、元组、`QSize`、`"24px"`、`"1.5em"` |
| `color`                                                    | 颜色，不填则跟随主题。可以是一个颜色，也可以是颜色映射表                  |
| `color_light_theme`                                        | 亮色主题下用的颜色，优先于 `color`                                        |
| `color_dark_theme`                                         | 暗色主题下用的颜色，优先于 `color`                                        |
| `selected_color`                                           | 列表/树里被选中时用的颜色（仅 `get_icon`，配合 item view 使用）           |
| `selected_color_light_theme` / `selected_color_dark_theme` | 同上，按主题分别指定                                                      |
| `hover_color`                                              | 鼠标悬停时用的颜色（仅 `IconWidget`；按钮悬停见 `set_icon`）              |
| `hover_color_light_theme` / `hover_color_dark_theme`       | 同上，按主题分别指定                                                      |
| `opacity`                                                  | 整体透明度，0—1，默认 1.0                                                 |
| `width` / `height`                                         | 需要非正方形时才用，优先于 `size`                                         |
| `rotate`                                                   | 旋转角度，写 `90` 就是 90 度                                              |
| `spin`                                                     | 持续旋转，用于加载中                                                      |
| `h_flip` / `v_flip`                                        | 水平 / 垂直翻转                                                           |
| `qss`                                                      | QSS 分组标签，空格分隔多个值，仅 `IconWidget` 有                          |

三个颜色参数都接受：颜色名 / HEX 3·4·6·8 位 / `rgb()` / `rgba()` / `hsl()` / `hsla()` / 元组 / `QColor`，或一张 `{原色: 新色}` 的映射表。

`get_icon` 不填颜色时跟随应用调色板；`IconWidget` 跟随控件自身调色板。

### size 能传什么

```python
size=24                  # 数字，最常用
size=24.5                # 小数也行
size=(24, 32)            # 元组，宽 × 高
size=QSize(24, 32)       # Qt 对象
size="24px"              # 带单位的字符串
size="1.5em"             # 跟随控件字号
```

| 写法           | 说明                                      |
| -------------- | ----------------------------------------- |
| 数字           | 逻辑像素，正方形边界                      |
| 元组 / `QSize` | 宽 × 高，等同于分别写 `width` 和 `height` |
| `"24px"`       | 和数字一样，写单位只是更明确              |
| `"1.5em"`      | 控件当前字号的 1.5 倍                     |

非正数、无法解析的字符串报 `InvalidSizeError`。

### em 跟随字号

```python
IconWidget("mdi:home", size="1em")
```

图标大小等于所在控件的字号。**字号变了图标自动跟着变**，适合放在文字旁边：

```python
label_layout.addWidget(IconWidget("mdi:alert", size="1em"))
label_layout.addWidget(QLabel("磁盘空间不足"))
```

要点：

- `1em` = 控件字体的像素大小，用 `QFontMetrics` 取
- 字号变化时重新计算，不用手动刷新
- `get_icon` 没有控件上下文，`em` 按应用默认字号算

`em` 是可选的便利写法，**不确定就用数字**，行为最直接。

### size 用逻辑像素，高分屏自动处理

`size=24` 的意思是 **24 个逻辑像素**，不是物理像素。

在 150% 缩放的屏幕上，我们实际会按 36 个物理像素渲染，但它在屏幕上看起来仍然和 100% 屏幕上的 24 像素一样大。

```python
IconWidget("mdi:home", size=24)   # 任何屏幕上视觉大小一致
```

**你不需要为高分屏做任何事。** 也不要自己乘缩放比，那会导致图标过大。

### 为什么不会糊

普通做法是准备一张 24×24 的图，在 150% 屏幕上被系统拉伸到 36×36，边缘就会模糊。

我们是矢量数据，**按实际需要的物理像素重新渲染**，所以任何缩放比下都清晰。

Qt 的 `QIconEngine` 会把屏幕缩放比传给我们（`scaledPixmap` 的 `scale` 参数，size 本身是设备无关像素），我们据此生成对应分辨率的图。

多屏幕、不同缩放比的情况也能处理：窗口拖到另一块屏幕时按新的缩放比重新渲染。

**这条要真机验证**，特别是 125% 这种非整数倍缩放，以及跨屏拖动。Step 1 和 Step 3 都会测。

### 和官方属性的对照

官方 `@iconify/react` 的属性（已核对本地源码）：

| 官方属性                   | 本库                                    |
| -------------------------- | --------------------------------------- |
| `icon`                     | 第一个参数                              |
| `width` / `height`         | `width` / `height`，另加更好用的 `size` |
| `color`                    | `color`                                 |
| `rotate`                   | `rotate`，改成角度值                    |
| `flip` / `hFlip` / `vFlip` | `h_flip` / `v_flip`                     |
| `inline`                   | 不做，Qt 布局里没有文字基线对齐的需求   |
| `mode`                     | 不做，那是网页的背景图/遮罩渲染方式     |
| `onLoad`                   | 改成 `loaded` 信号                      |
| `ssr`                      | 不做，网页服务端渲染专有                |
| `fallback`                 | `fallback`，图标不存在时的替代图标      |
| `className`                | Qt 动态属性 + QSS 属性选择器            |
| `style`                    | `setStyleSheet()`，Qt 原生方法          |

**官方没有 `scale` 参数。** 缩放就是靠 `width` / `height`：默认高度为 `1em`（跟随字号），宽度按比例算。

仓库里唯一出现 `scale` 的地方是构建期工具的选项（`IconifyLoaderOptions.scale`），用来设定图标相对 `1em` 的倍数，跟组件属性无关。

我们不引入 `scale`：Qt 里没有 `1em` 这种相对单位，直接给像素数更直接。`size=24` 比 `scale=1.5` 好理解。

### rotate 接受任意角度

```python
IconWidget("app:square", rotate=90)
IconWidget("app:square", rotate=45)
```

- 单位是度，不是弧度。`90` 就是 90 度。
- 任意角度都可以，包括 `45`、`12.5`。
- `360` 等同 `0`，`-90` 等同 `270`，自动归一。
- 只接受数字，传字符串报 `InvalidRotationError`。

**图形始终完整显示在 `size` 范围内，不会被裁掉。** 斜放时图形会自动缩小一点（45 度约为 0.71 倍），缩放比例随角度连续变化，不会突然跳变。想让图标看起来更大就调 `size`。

内部实现分两条路，使用者不必关心：90 度倍数走 SVG 变换（尺寸精确），其他角度在绘制时旋转。

### color 能传什么

写着顺手就行，全都支持：

```python
color="red"                      # 颜色名
color="#f00"                     # HEX 3 位
color="#ff0000"                  # HEX 6 位
color="#ff000080"                # HEX 8 位，末尾是透明度
color="#f008"                    # HEX 4 位，末尾是透明度
color="rgb(255, 0, 0)"           # RGB
color="rgba(255, 0, 0, 0.5)"     # RGBA
color="hsl(0, 100%, 50%)"        # HSL
color="hsla(0, 100%, 50%, 0.5)"  # HSLA
color=(255, 0, 0)                # 元组
color=(255, 0, 0, 128)           # 元组，带透明度
color=QColor("red")              # Qt 对象
color=Qt.red                     # Qt 枚举
```

规则：

| 写法                        | 说明                                                |
| --------------------------- | --------------------------------------------------- |
| 颜色名                      | SVG / CSS 标准名，`red`、`steelblue`、`transparent` |
| HEX                         | 3、4、6、8 位，大小写不限，`#` 可省略               |
| `rgb()` / `rgba()`          | 数值 0—255 或百分比；alpha 用 0—1 小数或百分比      |
| `hsl()` / `hsla()`          | 色相 0—360，饱和度和亮度用百分比                    |
| 元组                        | 整数 0—255，三个或四个                              |
| `QColor` / `Qt.GlobalColor` | 直接接受                                            |

无法识别时报 `InvalidColorError`，**不会静默变成黑色**。

### 带透明度的 HEX 默认是 RGBA

**透明度在最后：`#RRGGBBAA`，简写 `#RGBA`。**

```python
color="#ff000080"   # 半透明的红色
color="#f008"       # 同上的简写
```

这样从取色器直接粘贴就是对的。Figma、Photoshop、Sketch、浏览器 DevTools 和 CSS 标准都是这个顺序。

### 需要 Qt 顺序时显式声明

Qt 自己用的是 `#AARRGGBB`（透明度在前），主要出现在手写 Qt 代码和 QSS 里。这种字符串要显式转一下：

```python
from pyside_iconify import hex_argb, hex_rgba

color=hex_argb("#80ff0000")    # Qt 顺序，透明度在前
color=hex_rgba("#ff000080")    # CSS 顺序，透明度在后（同默认）
```

**为什么不自动识别？** 两种顺序都是合法的 8 位 HEX，没法从字符串本身判断。猜错会静默给出错误颜色，比报错更糟。

不带透明度的 3 位、6 位没有这个问题，两边一样。

### 不填 color 时自动跟随亮暗主题

这是本库的一个重点能力。

```python
IconWidget("mdi:home")   # 不填颜色
```

- 亮色主题 → 图标是深色
- 暗色主题 → 图标是浅色
- 用户中途切换主题 → **自动变，不用你写任何代码**

原理：取所在控件的文字颜色（`palette` 的 `WindowText` / `ButtonText`），和旁边的文字保持一致。所以图标不会出现「主题切了但图标还是黑的」这种问题。

### 禁用状态用透明度变淡

```python
button.setEnabled(False)
```

按钮禁用时，图标**整体透明度降到 0.4**，不改颜色。

选透明度而不是换成灰色，因为：

- 多色图标也能正确变淡，换灰色会毁掉配色
- 深浅主题下都成立，不用分别准备禁用色
- 视觉上和 Qt 原生禁用效果接近

    0.4 是默认值，可以全局调：

```python
from pyside_iconify import set_disabled_opacity

set_disabled_opacity(0.35)
```

### 整体调透明度

```python
IconWidget("mdi:home", opacity=0.5)
```

`opacity` 作用于整个图标，包括多色图标。想让某个图标淡一点但不改颜色时用它。

### 多个透明度相乘

透明度可能来自三个地方，**最终结果是它们相乘**：

```text
最终透明度 = 颜色自带的 alpha × opacity 参数 × 状态系数
```

例子：

```python
IconWidget("mdi:home", opacity=0.5)   # 放在一个禁用的按钮上
```

`0.5 × 0.4 = 0.2`，图标透明度 20%。

再举一个：

```python
IconWidget("mdi:home", color="#ff000080", opacity=0.5)
```

颜色自带 alpha 是 `0x80` ≈ 0.5，乘 `opacity` 0.5，得 0.25。禁用时再乘 0.4，最终 0.1。

**相乘而不是取最小值或覆盖**，这样每一层的意图都会保留：设了半透明的图标，禁用后应该比正常状态更淡，而不是一样淡。

### 旋转动画

```python
IconWidget("mdi:loading", spin=True)
```

持续顺时针旋转，用于加载中。默认转速 **每圈 1 秒**，可以调：

```python
IconWidget("mdi:loading", spin=True, spin_period=0.8)   # 每圈 0.8 秒
```

要点：

- 控件不可见时**自动暂停**，不浪费 CPU
- `spin` 和 `rotate` 可以同时用，`rotate` 是起始角度
- 多个图标同转会共用一个定时器，不会每个都开一个

`get_icon` 返回的 `QIcon` 也支持 `spin`，但 **`QIcon` 本身不会自己动**——它不知道要重绘谁。需要动画时用 `IconWidget`，或者自己定时调用目标的 `update()`。

**这条要真机验证**：几十个图标同时转时的 CPU 占用，以及窗口最小化后是否真的停下来。

### 想给亮暗指定不同颜色

用 `color_light_theme` 和 `color_dark_theme`：

```python
IconWidget("mdi:home", color_light_theme="#333333", color_dark_theme="#eeeeee")
```

只写一个也行，另一种主题下回退到自动跟随：

```python
IconWidget("mdi:home", color_dark_theme="#eeeeee")   # 亮色主题仍自动跟随
```

### 三个颜色参数的优先级

```text
color_light_theme / color_dark_theme  →  color  →  自动跟随主题
```

当前主题对应的那个参数优先。举例：

```python
IconWidget("mdi:home", color="red", color_dark_theme="#eeeeee")
```

- 亮色主题 → 红色（用 `color`）
- 暗色主题 → 浅灰（用 `color_dark_theme`）

**`color` 相当于「两种主题的默认值」**，`color_light_theme` / `color_dark_theme` 是对单个主题的覆盖。

### 什么时候不会自动跟随

| 情况                                    | 行为               |
| --------------------------------------- | ------------------ |
| 写了 `color="red"` 且没有对应主题的覆盖 | 固定红色，不跟主题 |
| 多色图标只传了一个颜色字符串            | 保持原配色         |
| 用 `get_icon` 且没有上下文控件          | 跟随应用调色板     |

**这条要真机验证**：Windows 系统主题切换、QSS 换肤、`setPalette` 三种方式都要能触发更新，不能只在应用重启后才对。

### 颜色可以是一个值，也可以是一张映射表

三个颜色参数都接受两种形式：

```python
# 一个颜色：给单色图标用
IconWidget("mdi:home", color="red")

# 一张映射表：给多色图标用，把原色换成新色
IconWidget("devicon:google", color={"#4285f4": "#00a0ff"})
```

规则：

| 图标类型 | 传一个颜色             | 传映射表                         |
| -------- | ---------------------- | -------------------------------- |
| 单色     | 生效，整体染色         | 需要包含 `currentColor` 键才生效 |
| 多色     | **不替换，保持原配色** | 按表替换对应的颜色               |

多色图标传单个颜色**故意不生效**——把 Google 图标染成一片红没有意义，这也是官方的行为。想改就明确说明改哪个颜色。

映射表只替换匹配到的颜色，没列出的保持原样：

```python
IconWidget("devicon:google", color={"#4285f4": "#00a0ff"})   # 只换蓝色，其余三色不动
```

### 多色图标也能跟随主题

```python
IconWidget("devicon:google",
           color_light_theme={"#ffffff": "#f5f5f5"},
           color_dark_theme={"#ffffff": "#2b2b2b"})
```

适合图标里有白底、白描边的情况——暗色主题下把白色换掉，不然会很刺眼。

### 映射表的匹配规则

- 键和值都走同一套颜色解析，`"#4285f4"`、`"rgb(66,133,244)"`、`QColor` 都行
- 键按**解析后的颜色值**匹配，不是按字符串。所以 `"#4285F4"`、`"#4285f4"`、`"rgb(66,133,244)"` 都能匹配到同一个颜色
- 表里的颜色图标中不存在时不报错，静默跳过
- 想知道图标里有哪些颜色：`get_icon_colors("devicon:google")`

最后一条是为了让你能先看再写映射表，不用去翻 SVG 源码。

### 长期固定的换色建议先存起来

```python
data = get_icon_data("devicon:google")
data = data.replace_colors({"#4285f4": "#00a0ff"})
add_icon("app:google-blue", data)
```

映射表参数适合临时、跟主题变化的场景；**固定不变的换色做一次存成新图标更划算**，渲染时少一道替换。

## 2.3 方法和信号

方法：`setIcon`、`setSize`、`setColor`、`setColorLightTheme`、`setColorDarkTheme`、`setOpacity`、`setRotation`、`setSpin`、`setFlips`。

查询用：

| 函数                                | 作用                               |
| ----------------------------------- | ---------------------------------- |
| `is_monotone("mdi:home")`           | 是不是单色图标                     |
| `get_icon_colors("devicon:google")` | 列出图标里用到的颜色，方便写映射表 |

信号：

| 信号                    | 何时触发         |
| ----------------------- | ---------------- |
| `loaded(name)`          | 图标数据准备好了 |
| `failed(name, error)`   | 加载失败         |
| `statusChanged(status)` | 状态变化         |

状态取值：`empty`、`loading`、`ready`、`missing`、`error`。

**注意**：`loaded` 表示数据可用，不等于像素已经画到屏幕上。

### 每种状态显示什么

**加载中和不存在是两回事**，显示也不同：

| 状态      | 含义                 | 显示                               |
| --------- | -------------------- | ---------------------------------- |
| `empty`   | 没设图标             | 空白                               |
| `loading` | 正在取数据           | **空白**，占住位置                 |
| `ready`   | 正常                 | 图标                               |
| `missing` | 图标确实不存在       | **占位图标**（一个问号方框）+ 报错 |
| `error`   | 网络失败、数据损坏等 | **占位图标** + 报错                |

关键区别：

- **加载中显示空白**，因为它多半马上就好了。闪一下占位图反而更难看。
- **确认不存在才显示占位图标**，这是真出问题了，要让人看见。

占位图标是我们内置的一个简单图形，不依赖任何图标集合，**断网也能显示**。

### 换掉占位图标

```python
IconWidget("mdi:not-exist", fallback="mdi:help-circle")
```

也可以全局设：

```python
from pyside_iconify import set_default_config

set_default_config(fallback="mdi:help-circle")
```

`fallback` 本身也可能不存在，这时退回内置占位图，**不会无限找下去**。

不想要占位图就写 `fallback=None`，那样失败时显示空白，但仍然发 `failed` 信号。

## 2.4 用 QSS 控制样式

`IconWidget` 是普通 `QWidget`，可以用样式表。

### 用 color 控制图标颜色

```css
IconWidget {
    color: #333333;
}
```

这条能生效，因为我们本来就读控件的文字色。**不用改代码，样式表统一管颜色。**

配合状态选择器：

```css
QPushButton:hover IconWidget {
    color: #0078d4;
}
```

### 在构造时给 QSS 分组

`qss` 是为 QSS 定制准备的标签属性，内部写入 Qt 动态属性：

```python
IconWidget("mdi:home", qss="toolbar primary")
```

```css
IconWidget[qss~="toolbar"] {
    color: #666666;
}
IconWidget[qss~="primary"] {
    color: #0078d4;
}
```

- 多个标签用空格分隔，QSS 用 `~=` 匹配其中一个。
- `qss` 只负责让选择器找到这个图标，不承载样式文本。
- 它不是 Web 的样式文本参数，只负责 QSS 分组。

### 直接写 QSS：就用 Qt 原生 setStyleSheet

这正是 PySide 的标准写法，不需要额外参数：

```python
self.setStyleSheet("""
IconWidget[qss~="toolbar"] {
    color: #cbd2dd;
    background: #111111;
}

IconWidget[qss~="toolbar"]:disabled {
    color: #6f7782;
}
""")
```

创建时：

```python
icon = IconWidget("mdi:home", qss="toolbar")
```

如果只想给某一个图标临时写样式，也是 Qt 原生方法：

```python
icon.setStyleSheet("color: red; background: #111111;")
```

**职责分开：** `qss` 用来分组；`setStyleSheet()` 用来写真正的 QSS。这样保留 PySide 原生工作流，也不用在构造函数里塞一大段样式字符串。

运行中换分组时，Qt 不会自动重算样式，需要刷新：

```python
icon.setProperty("qss", "danger")
icon.style().unpolish(icon)
icon.style().polish(icon)
icon.update()
```

### 优先级

```text
显式参数  →  QSS  →  自动跟随主题
```

```python
IconWidget("mdi:home", color="red")   # QSS 里写什么都没用，就是红色
IconWidget("mdi:home")                # QSS 说了算，QSS 没说就跟随主题
```

**写死的参数优先级最高**，这样调用处的意图不会被外部样式表悄悄改掉。

### 支持范围

| QSS 属性                         | 是否生效                   |
| -------------------------------- | -------------------------- |
| `color`                          | 生效，控制图标颜色         |
| `background`、`background-color` | 生效，画在图标下面         |
| `border`、`padding`、`margin`    | **不生效**                 |
| `width`、`height`                | **不生效**，用 `size` 参数 |

边框和内边距不支持，是 Qt 的限制：纯 `QWidget` 子类只认 `background` 系列属性。需要边框就在外面套一个 `QFrame`。

**这条要真机验证**：Qt 要求自定义控件在绘制时主动调用样式引擎，样式表背景才会出现。实现时会照官方写法处理，但必须实测确认。

## 2.5 全局默认值

不想每处都写一遍相同参数时：

```python
from pyside_iconify import set_default_config

set_default_config(
    size=20,
    color="#333333",
    color_dark_theme="#dddddd",
    fallback="mdi:help-circle",
)
```

之后 `IconWidget("mdi:home")` 就用这套默认值。

可以设的项：

| 项目                                               | 说明                     |
| -------------------------------------------------- | ------------------------ |
| `size`                                             | 默认大小                 |
| `color` / `color_light_theme` / `color_dark_theme` | 默认颜色                 |
| `opacity`                                          | 默认透明度               |
| `fallback`                                         | 图标不存在时的替代图标   |
| `disabled_opacity`                                 | 禁用时的透明度，默认 0.4 |
| `spin_period`                                      | 动画周期，默认 1 秒      |

规则：

- **写在参数里的优先于全局默认**
- 只影响调用之后创建的图标，已存在的不变
- 传 `None` 表示恢复该项的内建默认值
- `get_default_config()` 可以查当前值

适合在应用启动时设一次，统一整个程序的图标风格。

## 2.6 两个入口怎么选

| 你想干什么                     | 用哪个       |
| ------------------------------ | ------------ |
| 界面上摆一个图标               | `IconWidget` |
| 给按钮、菜单、自己的控件设图标 | `get_icon`   |

```python
# 摆一个图标
layout.addWidget(IconWidget("mdi:home", color="red"))

# 给已有控件设图标
button.setIcon(get_icon("mdi:home", color="red"))
```

**两者参数完全一致**，选哪个只看目标是「一个新控件」还是「已有控件的图标属性」。

### 可选：set_icon

如果懒得记 `setIcon` / `setTabIcon` / `setWindowIcon` 这些方法名差异，可以用它：

```python
from pyside_iconify import set_icon

set_icon(button, "mdi:home")
set_icon(tab_widget, "mdi:file", 0)

# 按钮悬停变色：写 hover_color 系参数才启用，不写就没有悬停效果
set_icon(button, "mdi:home", hover_color="#d1242f")
set_icon(button, "mdi:home",
         hover_color_light_theme="#0969da",
         hover_color_dark_theme="#58a6ff")
```

**这只是便利函数，不是必需路径。** 直接 `setIcon(get_icon(...))` 效果一样，而且更直白。所以它不支持的目标类型，也不影响你使用——`get_icon` 本身没有类型限制。

两个只有 `set_icon` 才有的能力（`get_icon` 给不了，别绕过它）：

- **按钮悬停变色**：Qt 样式对按钮图标的 mode 请求不可靠，裸 `QIcon` 表达不了悬停，`set_icon` 内部用事件切换两份图标实现
- 目标是按钮时才会启用；列表/树的选中变色走 `get_icon` 的 `selected_color`

### 不接受的 QIcon 的目标

比如 `QLabel` 只收 `QPixmap`：

```python
label.setPixmap(get_pixmap("mdi:home", size=24))
```

`get_pixmap` 返回静态图，**不会自动刷新**。需要自动刷新就用 `IconWidget`。

## 2.7 用自己的图标（离线，Step 1 实现这个）

```python
from pyside_iconify import add_collection

add_collection({
    "prefix": "app",
    "width": 16,
    "height": 16,
    "icons": {
        "square": {
            "body": '<rect x="2" y="2" width="12" height="12" fill="currentColor"/>'
        }
    },
})

icon = IconWidget("app:square", size=24, color="red")
```

注册过的图标直接显示，不联网、不查缓存。格式与官方 JSON 一致，所以从 Iconify 仓库挑出来的数据可以直接用。

**本地注册优先于网络。** 同名图标以注册的为准，不会被下载结果覆盖。

### 完全离线发布（可选，特殊场景）

图标默认按需从网络获取，这是主路径。如果程序要跑在断网或内网环境，可以用打包工具在发布前把用到的图标固化下来，一条命令扫描 + 打包，运行时一行加载：

```python
from pyside_iconify import load_bundle

load_bundle("icons.json")
```

详细用法见[离线打包文档](07-offline-pack.md)。

## 2.8 高级用法

只有需要私有图标服务器、严格禁网、独立缓存时才用：

```python
from pyside_iconify import IconifyClient

client = IconifyClient(offline=True)
icon = IconWidget("app:square", client=client)
```

| 对象            | 用途                       |
| --------------- | -------------------------- |
| `IconRegistry`  | 管理一组图标数据           |
| `IconifyClient` | 控制下载、缓存、离线策略   |
| `LoadRequest`   | 预加载一批图标并等完成通知 |

不传时库内部使用共享的默认实例。**普通使用者不需要知道它们存在。**

## 2.9 出错时

### 会抛异常的（用错了 API）

| 错误                     | 含义                                    |
| ------------------------ | --------------------------------------- |
| `InvalidIconNameError`   | 图标名格式不对                          |
| `InvalidRotationError`   | 旋转角度不是数字                        |
| `InvalidSizeError`       | 尺寸不是正数                            |
| `InvalidOpacityError`    | 透明度不在 0—1 之间                     |
| `WrongThreadError`       | 在非主线程调用了 Qt 相关接口            |
| `InvalidColorError`      | 颜色值无法识别                          |
| `InvalidIconDataError`   | 注册的图标数据不合法                    |
| `DuplicateIconError`     | 重复注册同名图标，且没写 `replace=True` |
| `IconNotLoadedError`     | `get_icon` 要的数据还没就绪             |
| `UnsupportedTargetError` | `set_icon` 不认识这个目标类型           |
| `NoApplicationError`     | 还没创建 `QApplication` 就创建控件      |

这些都是调用方的问题，**立刻抛出，不静默忽略。**

### 只发信号不抛异常的（运行时状况）

| 错误                    | 含义                           |
| ----------------------- | ------------------------------ |
| `IconNotFoundError`     | 图标不存在（服务器明确说没有） |
| `OfflineError`          | 禁网且本地没有                 |
| `NetworkError`          | 连接失败、超时、DNS 错误       |
| `RateLimitError`        | 请求太频繁被限流               |
| `ServerError`           | 服务器返回 5xx                 |
| `InvalidResponseError`  | 返回的内容不是合法图标数据     |
| `ResponseTooLargeError` | 返回内容超出大小上限           |
| `UnsupportedSvgError`   | Qt 画不出这个 SVG              |
| `RequestCancelledError` | 请求被主动取消                 |
| `ClientClosedError`     | 客户端已关闭                   |

控件显示占位图并发出 `failed` 信号。**不在绘制过程中抛异常**，否则界面会崩。

### 只记录、不影响显示的

| 情况                           | 处理                         |
| ------------------------------ | ---------------------------- |
| 磁盘缓存写不进去（只读、满盘） | 继续用内存，记一条日志       |
| 缓存文件损坏                   | 丢弃重新获取                 |
| 批量加载部分失败               | 成功的正常显示，失败的单独报 |

**已经能显示的图标，不因为缓存问题变成失败。**

### 安全相关

图标数据里如果有脚本、外部链接、超大结构，会在解析阶段就被拒绝，报 `UnsafeIconDataError`。远程数据不能无条件信任。

### 一句话原则

**能立刻发现的错误就抛出，运行中的状况用信号报告，不影响显示的问题只记日志。** 任何情况下都不吞掉错误、不静默显示空白。

## 2.10 命名约定

- 包名 `pyside_iconify`，安装名 `pyside-iconify`。
- 数据操作用 Python 风格：`add_icon`、`load_icons`。
- 控件方法用 Qt 风格：`setIcon`、`setColor`。

混用的原因：控件要和 Qt 现有习惯一致，数据接口要符合 Python 习惯。

## 2.11 类型提示

**全库带类型标注**，并包含 `py.typed` 标记，IDE 和 mypy 都能识别。

```python
IconWidget("mdi:home", siz=24)   # IDE 直接标红，不用等运行
```

要求：

- 所有公开函数、参数、返回值都有标注
- 参数用明确的联合类型，不用 `Any`。例如颜色是 `str | QColor | tuple | dict[...]`
- 图标名、尺寸、颜色这些常用类型有别名，方便外部引用
- 内部实现也标注，但外部只依赖公开的部分

**这条对后续工具链是前提**：VSCode 插件、MCP 工具、文档生成都要靠类型信息。CI 里会跑类型检查，不通过就失败。

## 2.12 线程

**Qt 相关的都必须在主线程**：创建控件、取 `QIcon`、渲染。在别的线程调用会**明确报错**，而不是让它崩在奇怪的地方。

```python
threading.Thread(target=lambda: get_icon("mdi:home")).start()
# 报 WrongThreadError
```

**数据层可以多线程**：解析 JSON、注册图标是纯 Python，加锁保护，后台线程能用。

```python
# 可以：后台线程里预解析数据
threading.Thread(target=lambda: add_collection(big_json)).start()
```

这样划分的理由：预加载大量图标数据是合理需求，不该被迫在主线程做；但绘制本来就只能在主线程，假装支持只会埋雷。

## 2.13 调试

用标准 `logging`，logger 名 `pyside_iconify`：

```python
import logging
logging.getLogger("pyside_iconify").setLevel(logging.DEBUG)
```

**默认不输出任何东西**，不自己搞一套日志系统，也不往控制台打信息。

各级别记什么：

| 级别      | 内容                                      |
| --------- | ----------------------------------------- |
| `DEBUG`   | 缓存命中 / 未命中、渲染耗时、请求合并情况 |
| `INFO`    | 注册了哪些集合、配置变更                  |
| `WARNING` | 缓存写入失败、SVG 有不支持的内容          |
| `ERROR`   | 图标加载失败、数据非法                    |

子 logger 按模块分，例如 `pyside_iconify.network`，方便只看某一部分。

## 2.14 和 React 的对应关系

| React                      | 本库                                |
| -------------------------- | ----------------------------------- |
| `<Icon icon="mdi:home" />` | `IconWidget("mdi:home")`            |
| `width` / `fontSize`       | `size`                              |
| `color`                    | `color`                             |
| `className`                | Qt 动态属性 + QSS 属性选择器        |
| `style`                    | `setStyleSheet()`，Qt 原生方法      |
| `addCollection()`          | `add_collection()`                  |
| `onLoad`                   | `loaded` 信号                       |
| DOM 自动刷新               | 控件自动刷新；已有控件用 `set_icon` |

## 2.15 内部需要守住的规则

实现时要注意，但使用者不必关心：

- 图标切换后，先前那次加载的结果不能覆盖新图标。
- `rotate` 接收角度值。90 度倍数换算成 Iconify 数据的旋转次数走 SVG 变换；其他角度用绘制变换，并按角度计算缩放比，保证图形不超出 `size`。
- 旋转角度参与渲染缓存的键，不同角度不能互相复用位图。
- 透明度按「颜色 alpha × `opacity` × 状态系数」相乘得到最终值，任何一层都不覆盖另一层；结果钳制在 0—1。
- 禁用系数默认 0.4，可用 `set_disabled_opacity()` 全局调整；实现为整体透明度，不改颜色，多色图标同样适用。
- `spin` 用共享定时器驱动，控件不可见时暂停；定时器不在模块导入时创建，最后一个动画停止后释放。
- 颜色统一先解析成 `QColor` 再用，不把用户传的字符串直接塞进 SVG。颜色名和 3 / 6 位 HEX 可以直接交给 `QColor`；**带透明度的 HEX 必须自己解析**，因为默认按 `#RRGGBBAA` 而 `QColor` 按 `#AARRGGBB`。`rgb()` / `rgba()` / `hsl()` / `hsla()` 函数式写法 Qt 也不认，同样自己解析。
- `hex_argb()` / `hex_rgba()` 返回已解析好的颜色对象，不是字符串，避免再次被当成默认顺序解析。
- 颜色映射表的键按解析后的颜色值匹配，不按字符串比较，大小写和写法差异都要能匹配上。
- 颜色的选取顺序固定为：当前主题的 `color_light_theme` / `color_dark_theme` → `color` → 主题跟随色。三者都可以是单值或映射表，处理逻辑一致。
- 生效的颜色参数（含映射表内容）参与渲染缓存的键；主题切换要让缓存失效，不能沿用上一主题的位图。
- 映射表里图标中不存在的颜色静默跳过，不报错；但整个表都没匹配上时要能通过 `get_icon_colors` 自查，不留下「改了没反应」的黑盒。
- 只改颜色或大小时，不重新下载，也不中断正在进行的加载。
- 控件销毁后不再回调，不持有已删除的 Qt 对象。`set_icon` 的目标用弱引用，目标没了自动解绑。
- `set_icon` 按目标类型查适配器表，找不到就报错，不靠 `hasattr` 猜方法名。
- 多个控件请求同一图标，只发一次请求。
- 绘制过程中不做网络和磁盘等待。
- `loading` 与 `missing` 必须分开：只有确认不存在或出错才显示占位图，加载中一律空白。
- `fallback` 只找一层，替代图标也失败时用内置占位图，不递归查找。
- 内置占位图不依赖任何图标集合，断网、数据全空时也要能画出来。
- `size` 解析出的宽高统一成逻辑像素后再进缓存键；`em` 依赖控件字体，字体变化要重新计算并失效缓存。
- 全局默认值只在创建时取一次快照，之后改默认值不影响已创建的图标；缓存键用的是实际生效值，不是「是否使用了默认」。
- `IconWidget.paintEvent` 必须先用样式引擎画一遍控件本体（`QStyle.PE_Widget`），QSS 的背景才会出现；没设样式表时这步是空操作。
- 图标颜色从 `QStyleOption` 的 palette 取，不硬编码，QSS 的 `color` 才能生效。
- QSS 动态属性运行中变化后要让 Qt 重新算样式（`unpolish` / `polish`），否则 QSS 不会立即生效。
- QSS 解析出的颜色只在没有显式颜色参数时使用，顺序固定为：参数 → QSS → 主题跟随。
- Qt 相关调用做线程检查，非主线程直接报 `WrongThreadError`，不尝试跨线程转发。
- 数据层的注册表和缓存加锁，允许后台线程解析和注册。
- 日志只用标准 `logging`，默认不加 handler，不改根 logger 配置。
- 公开 API 全部带类型标注，包内放 `py.typed`。
