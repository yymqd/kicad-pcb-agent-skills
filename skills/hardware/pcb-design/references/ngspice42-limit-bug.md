# ngspice-42 `limit()` Regression Bug

## 现象

ngspice-42 (PPS 42+ds-3build1, 2024-03-31) 中：

| 函数 | 输入 | 期望输出 | 实际输出 | 状态 |
|:-----|:-----|:---------|:---------|:-----|
| `limit(3.0, 0.5, 2.0)` | V=3.0, lo=0.5, hi=2.0 | 2.0 | **-1.0** | ❌ |
| `limit(-1.0, 0.5, 2.0)` | V=-1.0, lo=0.5, hi=2.0 | 0.5 | **?** | ❌ |
| `if(V(1)>2, 2, 0.5)` | — | — | **不支持** | ❌ |
| `min(max(3.0, 0.5), 2.0)` | V=3.0, lo=0.5, hi=2.0 | 2.0 | **2.0** | ✅ |
| `min(max(-1.0, 0.5), 2.0)` | V=-1.0, lo=0.5, hi=2.0 | 0.5 | **0.5** | ✅ |

## 替代方案

用 `min(max(x, lo), hi)` 替换所有 `limit(x, lo, hi)`：

```spice
* ❌ 坏在 ngspice-42
B1 out 0 V=limit(V(in), 0.5, 9.0)
E1 out 0 VALUE {limit(V(in), 0.5, 9.0)}

* ✅ 可在 ngspice-42 工作
B1 out 0 V=min(max(V(in), 0.5), 9.0)
```

注意参数顺序不同：
- `limit(x, lo, hi)` → x 被限制在 [lo, hi] 区间
- `min(max(x, lo), hi)` → 先 max(取最低), 再 min(取最高)

## 适用范围

| 器件类型 | `limit()` | `min(max())` |
|:---------|:----------|:-------------|
| B-source (`V=...`) | ❌ | ✅ |
| E-source (`VALUE {...}`) | ❌ | ✅ |
| G-source | ❌ | 未测试 |

## 相关错误

在 ngspice-42 中 `if()` 函数也不可用：
```
Error: no such function 'if'
```
替代方案是用嵌套 `min(max())` 实现条件限幅。
