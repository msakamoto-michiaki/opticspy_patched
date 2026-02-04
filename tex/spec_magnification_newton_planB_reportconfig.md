# 倍率（β/α/γ）・ニュートン公式 実装仕様（案B / ReportConfig拡張）

本仕様書は、既存の `SurfaceSpec` / `ReportConfig` / reduced-angle ABCD（状態 `[y,u]`, `u=nθ`）の枠組みに対して、  
倍率（β/α/γ）およびニュートン公式を **有限共役まで扱える「案B（系行列ベース）」**で実装する設計案をまとめる。

- 既存の `compute_abcd_from_prescription()` / `compute_report()` と自然に接続する
- 足りないパラメータは **ReportConfigに追加**する
- recipe像面とparaxial像面の両方で比較可能にする（診断として有用）
- 物体位置 `z_o` と像面位置 `z_i` は **入力にも出力にもなり得る**（相互に解ける）

---

## 1. 前提（座標系・行列定義）

### 1.1 座標系
- 光は **+z 方向**へ進む（物体→像）
- `reference_surface` の頂点を **絶対座標 `z=0`** とする
- `start_surface` は通常 `reference_surface` と一致（例：2）
- 各面頂点位置 `z_k` は処方の厚み総和で決まる（既存の report の `z9` 等）

以降の `z` はすべて **reference頂点基準の絶対座標**で表す。

### 1.2 reduced-angle ABCD
状態ベクトル：
- `[y, u]^T`
- `u = n θ`

伝搬：
\[
T(t,n)=\begin{pmatrix}1 & t/n \\ 0 & 1\end{pmatrix}
\]

屈折（曲率半径R、入射側n1、出射側n2）：
\[
R(R,n_1,n_2)=\begin{pmatrix}1 & 0 \\ -(n_2-n_1)/R & 1\end{pmatrix}
\]

---

## 2. ReportConfig 拡張（追加パラメータ）

既存フィールド（例：`start_surface`, `end_surface`, `image_surface`, `reference_surface`, `wavelengths_nm`, `prescription`）に加え、倍率/ニュートンのために「面外伝搬」を指定する。

### 2.1 物体側（object side）
#### `object_distance_mm: Optional[float] = None`
- 物体面の絶対位置 `z_o` を表す（reference頂点基準）
- 通常、物体が入射側にあるので `z_o < 0`
- `None` は無限遠を意味する（推奨）

#### `object_medium: str = "air"`
- 物体側媒質名（屈折率計算に利用）
- まずは `air` のみで運用して良い（n=1）

### 2.2 像側（image side）
#### `image_mode: Literal["recipe","paraxial","absolute"] = "recipe"`
像面位置の決め方を3モードで表す。

- `"recipe"`：処方上の像面（像面直前面の thickness により `z_i` が決まる）
- `"paraxial"`：パラキシャル合焦面（BFL=-A/C により `z_i` を決める）
- `"absolute"`：`image_z_abs` を絶対指定（後述）

#### `image_z_abs: Optional[float] = None`
- `"absolute"` のときのみ使用
- 像面の絶対座標 `z_i` を直接指定する

#### `image_medium: str = "air"`
- 像側媒質名（n_i）

---

## 3. 物体・像の絶対座標と “入力/出力が逆になる” 問題の整理

### 3.1 絶対座標の定義（明確化）
- `z_o`：物体面の絶対座標（`ReportConfig.object_distance_mm`）
- `z_i`：像面の絶対座標（`image_mode` で決まる／または `image_z_abs`）

`z_o` と `z_i` は、運用によって
- `z_o` を入力して `z_i` を解く（有限共役の合焦面を求める）
- `z_i` を入力して `z_o` を解く（センサ位置固定で物体位置を求める）
の両方が可能である。

### 3.2 reduced距離（伝搬距離）への変換
- reference頂点 `z_ref = 0`
- end_surface頂点 `z_end`（処方から計算）

物体側（物体面→reference頂点）：
\[
d_o = z_{ref} - z_o = -z_o
\]
\[
L_o = d_o / n_o
\]

像側（end頂点→像面）：
\[
d_i = z_i - z_{end}
\]
\[
L_i = d_i / n_i
\]

---

## 4. レンズ部分系行列と全系行列（案Bの中心）

### 4.1 レンズ部分系行列 `M_lens`
既存の `compute_abcd_from_prescription()` で得る。

\[
M_{lens}=
\begin{pmatrix}
A & B\\
C & D
\end{pmatrix}
\]

- 範囲：通常 `start_surface..end_surface`（例：2..9）
- 波長：参照波長（通常 `wavelengths_nm` の中間）

### 4.2 物体側・像側伝搬行列
\[
T_o=
\begin{pmatrix}
1 & L_o\\
0 & 1
\end{pmatrix},
\quad
T_i=
\begin{pmatrix}
1 & L_i\\
0 & 1
\end{pmatrix}
\]

### 4.3 全系行列 `M_sys`
\[
M_{sys} = T_i\, M_{lens}\, T_o
=
\begin{pmatrix}
A_s & B_s\\
C_s & D_s
\end{pmatrix}
\]

---

## 5. 結像条件と共役解（zo ↔ zi の相互変換）

### 5.1 結像条件（近軸）
物体点が像面で一点に結像する近軸条件は **`B_s = 0`**。

`B_s` を展開すると：
\[
B_s = (A L_o + B) + (C L_o + D)\,L_i
\]

### 5.2 zo（=Lo）を与えて zi（=Li）を解く（有限共役の像面計算）
\[
\boxed{
L_i = -\frac{A L_o + B}{C L_o + D}
}
\]
\[
d_i = n_i L_i,\quad
\boxed{z_i = z_{end} + d_i}
\]

### 5.3 zi（=Li）を与えて zo（=Lo）を解く（物体位置計算）
\[
\boxed{
L_o = -\frac{B + D L_i}{A + C L_i}
}
\]
\[
d_o = n_o L_o,\quad
\boxed{z_o = z_{ref} - d_o = -d_o}
\]

> 注：`z_o` と `z_i` は状況に応じて入力/出力が入れ替わる。  
> 本仕様では、どちらも絶対座標で一貫して扱い、`L_o/L_i` に落として相互変換する。

---

## 6. 倍率（β/α/γ）の定義（案B）

### 6.1 横倍率 β（lateral magnification）
結像条件が満たされる（または十分小さい `B_s` の）とき、
\[
\boxed{\beta = A_s}
\]
を採用する。

- 解釈：像面で角度依存が消えると `y' = A_s y` となるため

### 6.2 角倍率 γ
reduced-angle のため、まず “u倍率” を定義する：
\[
\boxed{\gamma_u = D_s}
\]

角倍率（θ倍率）が必要なら媒質補正を入れる：
\[
\boxed{\gamma_\theta = (n_o/n_i)\,D_s}
\]
air→air なら `γθ ≈ Ds` で良い。

### 6.3 縦倍率 α（用語の曖昧性の解消）
「縦倍率」は解釈が分かれるため、本仕様では **2種類を明示**する。

- **(a) 縦倍率=横倍率（一般の“倍率”）**  
  \[
  \boxed{\alpha = \beta}
  \]
- **(b) 軸方向倍率（longitudinal magnification）**  
  \[
  \boxed{m_L = \beta^2\,(n_i/n_o)}
  \]
  出力名は `longitudinal_mag` として別に出す。

### 6.4 ピント指標（診断）
- `B_s` を必ず出力し、recipe像面のデフォーカス度合いの診断に使う
- `"paraxial"` モードでは `B_s≈0` になることが期待される（近軸合焦）

---

## 7. ニュートン公式（Newton relation）の定義とチェック

### 7.1 焦点位置の絶対座標（zf, zf'）
既存レポートの主平面と焦点距離を使い、焦点を絶対座標で定義する。

- `z_H`：前側主平面 H の絶対座標
- `z_H'`：後側主平面 H' の絶対座標
- `f`：焦点距離（EFL）

\[
\boxed{z_F = z_H - f}
\]
\[
\boxed{z_{F'} = z_{H'} + f}
\]

> 実装上：  
> - `H` は「start_surface頂点からの距離」  
> - `H'` は「end_surface頂点からの距離」  
> で出力される場合があるため、絶対化は  
> `z_H = z_start + H`（start=referenceなら `z_start=0`）  
> `z_H' = z_end + H'`  
> として扱う。

### 7.2 Newton距離 x, x' の定義（明確化）
ニュートン公式を `x x' = f^2` の形で扱うため、距離の向きを固定する。

- `x`：物体が前側焦点 F からどれだけ離れているか（**物体側へ正**）
\[
\boxed{x = z_F - z_o}
\]
- `x'`：像が後側焦点 F' からどれだけ離れているか（**像側へ正**）
\[
\boxed{x' = z_i - z_{F'}}
\]

これにより、同一媒質（air→air）で近軸結像が成立する場合
\[
\boxed{x\,x' = f^2}
\]
がチェック式となる。

### 7.3 運用ルール
- `object_distance_mm is None`（無限遠）の場合、Newtonチェックはスキップ（意味が薄い）
- `"recipe"` と `"paraxial"` の両方で `x*x'` と `f^2` を出して比較しても良い（診断向き）

---

## 8. 実装API案（abcd_report.py）

既存の `compute_report(cfg)` と整合するように、以下を追加する。

### 8.1 `compute_system_matrix(cfg, wavelength_nm=None) -> dict`
返す内容（例）：
- `A_s, B_s, C_s, D_s`
- `L_o, L_i`
- `z_end, z_i`
- `image_mode`

### 8.2 `compute_magnifications(cfg, wavelength_nm=None) -> dict`
返す内容（例）：
- `beta = A_s`
- `alpha = beta`
- `gamma_u = D_s`
- `gamma_theta = (n_o/n_i)*D_s`
- `longitudinal_mag = beta**2*(n_i/n_o)`
- `focus_indicator_B = B_s`

### 8.3 `compute_newton_check(cfg, wavelength_nm=None) -> Optional[dict]`
返す内容（例）：
- `z_o, z_i, z_F, z_Fp, x, xprime, f`
- `x_xprime, f2, rel_err`

`object_distance_mm is None` の場合は `None` を返す。

### 8.4 `compute_report(cfg)` への統合
`compute_report(cfg)` の戻り値に以下を追加する：

- `system_matrix`
- `magnifications`
- `newton_check`

---

## 9. 既存コードとの整合ポイント（重要）

- reduced-angle `u=nθ` を維持するため、伝搬は必ず `t/n` を使う
- `image_mode` により像面の取り方を切り替え、recipeとparaxialを比較可能にする
- 結像診断として `B_s` を必ず出す（recipe像面でのデフォーカス可視化）
- 媒質が変わる場合は `gamma_theta` に `n_o/n_i` の補正を入れる（まずはair→airで運用）

---

## 10. 最小導入セット（まず追加すべき ReportConfig）

最初に導入すべきフィールド最小セット：

- `object_distance_mm: Optional[float] = None`
- `object_medium: str = "air"`
- `image_mode: str = "recipe"`
- `image_medium: str = "air"`
- （必要時のみ）`image_z_abs: Optional[float] = None`

これで、
- 無限遠運用でも `γ`（角→像高/角倍率相当）や `B_s` を出せる
- 有限共役を入れた瞬間に `β/α/γ` と Newtonチェックが有効化できる

---

以上。
