# `test3_1.py` の `_quiet_call` と First-order 比較（opticspy vs ABCD direct）仕様書

このドキュメントは、`test3_1.py` における

- `_quiet_call` の目的と挙動
- `opticspy` の first-order 計算（`first_order_tools`）が何を意味し、どう計算しているか
- `optics/abcd_report.py` 側（ABCD direct）が、どのように同等の指標を計算しているか
- `_quiet_call` がどこでどう使われるか（使われないか）

を、**仕様書として**まとめたものです。

---

## 1. `_quiet_call` の仕様

### 1.1 目的
`opticspy.ray_tracing.first_order_tools` の各関数は内部で `print()` を行うことがあり、テスト実行ログが大量に汚れる。  
`_quiet_call` は **計算結果は保持したまま、標準出力（stdout）への表示だけを抑制**するためのラッパである。

### 1.2 実装（代表）
```python
def _quiet_call(fn, *args, **kwargs):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        return fn(*args, **kwargs)
```

### 1.3 動作
- `contextlib.redirect_stdout(buf)` により、コンテキスト内の `print()` 出力先が `buf` に切り替わる
- `fn(*args, **kwargs)` の **戻り値はそのまま返る**
- **計算ロジック・数値結果は一切変化しない**
- 抑制されるのは stdout のみであり、例外はそのまま伝播する

---

## 2. `opticspy first-order` 側の計算仕様（意味と計算方法）

`test3_1.py` では以下のように opticspy の first-order を呼び出す：

```python
from opticspy.ray_tracing import first_order_tools as fot

opt_efl_full   = _quiet_call(fot.EFL, L, cfg.start_surface, cfg.end_surface)
opt_efl_23     = _quiet_call(fot.EFL, L, 2, 3)
opt_bfl_recipe = _quiet_call(fot.BFL, L)
opt_img_pos    = _quiet_call(fot.image_position, L)
opt_ep         = _quiet_call(fot.EP, L)
opt_ex         = _quiet_call(fot.EX, L)
opt_oal_27      = _quiet_call(fot.OAL, L, 2, 7)
```

ここで `L` は opticspy の `Lens` インスタンス（`build_opticspy_lens` により生成）。

### 2.1 `EFL(L, start, end)`（= `EFY()` 相当）
**意味**：指定範囲のパラキシャル有効焦点距離（EFL）。  
**計算**：
- 指定範囲 `start..end` の reduced-angle ABCD 行列を構築
- 行列の `C` 成分から：
\[
\mathrm{EFL} = -\frac{1}{C}
\]
- opticspy 実装は途中で `start surface:` 等を `print()` することがあるため `_quiet_call` が必要

`EFL(L,2,3)` は **部分系**（面2〜3）の EFL を同じ式で算出する。

### 2.2 `BFL(L)`（重要：opticspy の BFL は “処方厚み”）
**意味**：像面直前面（最後から2番目 surface）の thickness。  
**計算**：ABCD ではなく、`surface_list[-2].thickness` を返す（処方の値）。

> これは「後側焦点距離（paraxial BFL = -A/C）」ではない。  
> opticspy の `BFL()` は本仕様書では **`BFL_recipe`** と呼ぶ。

### 2.3 `image_position(L)`
**意味**：物体距離を含むパラキシャル像位置（opticspy 実装の式に従う）。  
**計算（実装準拠）**：
- `z = L.object_position`
- `f = -1/C`（EFL）
- `Fp = -A/C`（paraxial BFL）
- \[
\mathrm{image\_position} = Fp + \frac{f^2}{z}
\]
無限遠物体（`z` が大きな負値）では `f^2/z ≈ 0` となり、ほぼ `Fp` に一致する。

### 2.4 `EP(L)`（Entrance Pupil position）
**意味**：入口瞳位置（STOP 面を基準に定義される、opticspy 実装の式に従う）。  
**計算（概略）**：
- STOP 面（`STO`）を探索
- STOP 手前までの部分系 ABCD（例：`start=2, end=stop-1`）を構築
- opticspy の first_order_tools が持つ \(P, P', \phi, l, l'\) を用いる式で `EP` を算出
- 実装は途中ログを `print()` することがあるため `_quiet_call` を用いる

### 2.5 `EX(L)`（Exit Pupil position）
**意味**：出口瞳位置（STOP 面以降の部分系に基づく）。  
**計算**：
- STOP 後ろ側の部分系 ABCD を構築（例：`stop+1 .. last`）
- EP と対称な opticspy 実装式により算出

### 2.6 `OAL(L, start, end)`（Overall Axial Length）
**意味**：指定範囲の軸上全長（厚み総和）。  
**計算**：
\[
\mathrm{OAL} = \sum_{i=start}^{end-1} t_i
\]
ABCD は不要で、処方 thickness の総和で決まる。

---

## 3. `ABCD direct` 側（`optics/abcd_report.py`）の計算仕様

### 3.1 行列構築：`compute_abcd_from_prescription(...)`
`SurfaceSpec` 列（処方）から reduced-angle ABCD 行列を直接構築する。

- 状態ベクトル：\([y,u]\), ただし \(u=n\theta\)
- 伝搬（厚み t, 媒質屈折率 n）：
\[
T = \begin{pmatrix}1 & t/n \\ 0 & 1\end{pmatrix}
\]
- 屈折（半径 R, 左右屈折率 \(n_1,n_2\)）：
\[
R = \begin{pmatrix}1 & 0 \\ -(n_2-n_1)/R & 1\end{pmatrix}
\]
- 指定範囲 `start..end` で屈折と伝搬を順に積算し、\(A,B,C,D\) を得る
- 屈折率 \(n(\lambda)\) は opticspy の `glass_funcs.glass2indexlist()` を用い、**参照波長（中間波長）**で一致させる

### 3.2 opticspy互換 first-order：`first_order_like_opticspy(cfg, object_distance)`
opticspy の first_order_tools と **同じ意味・同じ式**で指標を計算する。

主要項目：

- `EFY`（EFL）：
\[
f' = -\frac{1}{C}
\]
- `BFL_paraxial`（paraxial BFL）：
\[
\mathrm{BFL}_{\mathrm{parax}} = -\frac{A}{C}
\]
- `image_position`（opticspy 実装準拠）：
\[
\mathrm{image\_position} = -\frac{A}{C} + \frac{(-1/C)^2}{z}
\]
- `BFL_recipe`（opticspy `BFL()` と同義）：
  - 像面直前面の厚み（処方から取得）
- `EP/EX`：
  - STOP 面を探索し、前後の部分系 ABCD を作って opticspy と同じ式で算出
- `OAL`：
  - 厚み総和のため、`oal_from_prescription()` で算出（ABCD不要）

### 3.3 比較用に別計算する項目
`test3_1.py` では、以下を明示的に別計算して比較する：

- `EFY(2,3)`：`compute_abcd_from_prescription(..., 2, 3)` で部分系 ABCD を作り、\(f'=-1/C\)
- `OAL(2,7)`：`oal_from_prescription(prescription, 2, 7)` で厚み総和

---

## 4. `_quiet_call` の適用範囲（重要）

- `_quiet_call` を適用するのは **opticspy first-order 呼び出しのみ**
- `ABCD direct` 側は原則として `print()` を行わないため `_quiet_call` は不要

すなわち：

- `opticspy first-order`：`_quiet_call(...)` で stdout を吸い込む
- `our ABCD direct`：通常呼び出し（stdoutに出力しない）

---

## 5. 比較ログの解釈（一致すべき/仕様差で異なる）

### 5.1 一致が期待されるもの
- `EFY full` / `EFY(2..3)`：ABCD定義と屈折率が一致していれば、数値誤差程度で一致
- `image_position`：`object_position` の定義が一致していれば一致
- `EP/EX`：STOP面の解釈と部分系範囲が一致していれば一致
- `OAL`：厚み総和のため一致

### 5.2 混同しやすい（仕様差で異なり得る）もの
- `BFL()`：opticspy は **処方の最後厚み**（`BFL_recipe`）
- `BFL_paraxial`：ABCDから計算する **パラキシャル焦点距離**（`-A/C`）

この2つの差は：
- `.seq` で像面がパラキシャル焦点に合わせられていない場合の「デフォーカス量」
として解釈できる。

---

以上。
