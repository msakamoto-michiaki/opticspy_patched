# `abcd_report.py` 拡張版 仕様書（倍率 β/α/γ・ニュートン公式・有限共役モード）  
**対象**：`optics/abcd_report.py`（v9 系：Plan B 実装＋有限共役テスト `test1_2` を想定）  
**目的**：ABCD 直接計算に基づき、カーディナル点・像面チェックに加えて、  
(1) **全系行列（object→image）**、(2) **倍率（β/α/γ）**、(3) **ニュートン公式チェック**を一貫した座標・符号規約で提供する。

---

## 0. 背景と設計方針

本プロジェクトでは、`SurfaceSpec` と `ReportConfig` から **近軸（パラキシャル）**の AB-CD 行列を積算し、レンズの一次特性（EFL、主平面、BFL、瞳位置など）を求める。  
拡張版では、さらに

- **有限共役（物体距離が有限）**を扱える
- 像面の選び方を `recipe / paraxial / absolute` で切替可能
- その上で、**結像条件（Bs=0）**、**横倍率 β**、**角倍率 γ**、**ニュートン公式**を同じ定義で出す

ことを狙う。

> 重要：本仕様の倍率は **パラキシャル（一次）**の量であり、収差・口径食・実効開口制限などは含まない。  
> ただし `Bs` の値は「その像面が近軸的に合焦しているか（角度依存が消えているか）」の診断に非常に有効である。

---

## 1. 記号・量の定義（必須：ここが基準）

### 1.1 座標系（絶対 z 座標）
- 光は **+z 方向**へ進む（物体側 → 像側）
- `reference_surface` の頂点を **絶対座標の原点**とし  
  \[
  z_{\mathrm{ref}} = 0
  \]
- 各面頂点位置 \(z_k\) は処方厚みの累積で得る（`z_k` は mm）

このため、**物体面・像面は絶対座標 \(z_o, z_i\)（mm）で表す**。

### 1.2 reduced-angle 形式のレイベクトル
状態ベクトルは
\[
\mathbf{r}=\begin{pmatrix}y\\u\end{pmatrix},
\qquad u = n\,\theta
\]
- \(y\)：光軸からの高さ（mm）
- \(\theta\)：光軸に対する角（rad、近軸）
- \(n\)：その区間の屈折率
- \(u\)：reduced-angle（屈折率を掛けた角度成分）

> 空気（\(n\approx1\)）では \(u\approx \theta\)。

### 1.3 ABCD 行列の意味
ある系が \(\mathbf{r}\) を \(\mathbf{r}'\) に写すとき
\[
\begin{pmatrix}y'\\u'\end{pmatrix}
=
\begin{pmatrix}A&B\\C&D\end{pmatrix}
\begin{pmatrix}y\\u\end{pmatrix}
\]
で定義する。

---

## 2. 基本行列（伝搬・屈折）と積算

### 2.1 伝搬（厚み t, 媒質 n）
\[
T(t,n)=\begin{pmatrix}1 & t/n\\0&1\end{pmatrix}
\]
- \(t\)：厚み（mm）
- reduced-angle のため **必ず \(t/n\)** が現れる。

### 2.2 屈折（曲率半径 R, 入射側 n1, 出射側 n2）
\[
R(R,n_1,n_2)=\begin{pmatrix}1 & 0\\-(n_2-n_1)/R & 1\end{pmatrix}
\]
- \(R\)：曲率半径（mm、正負は光学符号規約に従う）
- power 成分は \(-(n_2-n_1)/R\)。

### 2.3 レンズ部分系行列 \(M_{\mathrm{lens}}\)
`start_surface..end_surface` の範囲を「レンズ部分系」とし、
\[
M_{\mathrm{lens}}=
\begin{pmatrix}A&B\\C&D\end{pmatrix}
\]
を積算で求める。

---

## 3. カーディナル点（従来機能の位置づけ）

`compute_report()` は参照波長で \(A,B,C,D\) を求め、以下を提供する（空気→空気を想定）：

- **有効焦点距離（EFL）**  
  \[
  f' = -\frac{1}{C}
  \]
- **パラキシャル BFL**（最終屈折面頂点から焦点まで）  
  \[
  \mathrm{BFL}_{\mathrm{parax}} = -\frac{A}{C}
  \]
- 主平面位置 \(H, H'\)（実装の符号規約に従う）
- `Image plane check`：recipe像面と paraxial焦点の差（Δz）

> 注意：opticspy の `BFL()` は「処方上の最後厚み（recipe）」を返すため、  
> \(\mathrm{BFL}_{\mathrm{parax}}\)（ABCD由来）とは一致しないことがある。差はデフォーカス指標として解釈できる。

---

## 4. 拡張：物体側・像側の面外伝搬と全系行列（Plan B）

### 4.1 追加パラメータ（ReportConfig 拡張）
- `object_distance_mm: Optional[float]`  
  - **物体面の絶対座標** \(z_o\)（mm）  
  - 物体が入射側なら通常 \(z_o<0\)  
  - `None` は無限遠入力（物体面を置かず角入力に近い運用）を意味する
- `object_medium: str`（既定 `"air"`）→ \(n_o\)
- `image_mode: "recipe"|"paraxial"|"absolute"`
- `image_z_abs: Optional[float]`（`absolute` の場合に像面絶対座標 \(z_i\) を指定）
- `image_medium: str`（既定 `"air"`）→ \(n_i\)

### 4.2 物体側伝搬 \(T_o\)
物体面 → start_surface頂点（多くは reference と一致）までの距離を
\[
d_o = z_{\mathrm{start}} - z_o
\]
reduced距離
\[
L_o = \frac{d_o}{n_o}
\]
とし、
\[
T_o=\begin{pmatrix}1&L_o\\0&1\end{pmatrix}
\]
を導入する。

- 無限遠（`object_distance_mm=None`）のときは **規約として \(L_o=0\)**（\(T_o=I\)）とする。  
  これは「物体面を置かない（角入力）」モードであり、有限共役の“横倍率”の解釈は弱くなる。

### 4.3 像側伝搬 \(T_i\) と像面位置 \(z_i\)
end_surface頂点の絶対位置を \(z_{\mathrm{end}}\) とし、像面まで
\[
d_i = z_i - z_{\mathrm{end}},\qquad L_i = \frac{d_i}{n_i}
\]
\[
T_i=\begin{pmatrix}1&L_i\\0&1\end{pmatrix}
\]

`image_mode` により \(z_i\) を決める：

- **recipe**：処方の最後厚み（像面直前面厚み）から \(z_i\) を決定  
- **absolute**：`image_z_abs` をそのまま採用  
- **paraxial**：  
  - 無限遠入力（`object_distance_mm=None`）  
    → \(\mathrm{BFL}_{\mathrm{parax}}=-A/C\) を用いて \(z_i=z_{\mathrm{end}}+\mathrm{BFL}_{\mathrm{parax}}\)  
  - **有限共役（`object_distance_mm` が有限）**  
    → **結像条件 \(B_s=0\) から共役合焦面を解く**（後述）

### 4.4 全系行列（object→image）
\[
M_{\mathrm{sys}} = T_i\, M_{\mathrm{lens}}\, T_o
=
\begin{pmatrix}
A_s&B_s\\C_s&D_s
\end{pmatrix}
\]

---

## 5. 有限共役の結像条件と像面解（paraxial mode の核心）

### 5.1 結像条件 \(B_s=0\)
全系で
\[
\begin{pmatrix}y_i\\u_i\end{pmatrix}
=
\begin{pmatrix}A_s&B_s\\C_s&D_s\end{pmatrix}
\begin{pmatrix}y_o\\u_o\end{pmatrix}
\]
としたとき、物体点 \(y_o\) の像高が入射角成分 \(u_o\) に依存しない（＝点結像）条件が
\[
\boxed{B_s = 0}
\]
である（近軸結像条件）。

`B_s` を展開すると
\[
B_s = (A\,L_o + B) + (C\,L_o + D)\,L_i
\]

### 5.2 物体位置 \(z_o\) を入力して像面 \(z_i\) を解く（有限共役の合焦）
有限共役で `image_mode="paraxial"` の場合は、上の \(B_s=0\) を満たす \(L_i\) を
\[
\boxed{
L_i = -\frac{A L_o + B}{C L_o + D}
}
\]
で求め、
\[
d_i = n_i L_i,\qquad \boxed{z_i = z_{\mathrm{end}} + d_i}
\]
とする。

> ここで `focus_indicator_B = B_s` は合焦の品質診断になる。  
> `|B_s|` が非常に小さい（例：1e-10 以下）なら、パラキシャル合焦面を機械精度で得られている。

---

## 6. 倍率（β/α/γ）定義（Plan B）

### 6.1 横倍率 β（lateral magnification）
結像条件が満たされる（または十分小さい \(B_s\) の）とき、
\[
\boxed{\beta = A_s}
\]
を横倍率とする。  
実像形成では通常 \(\beta<0\)（倒立像）となる。

### 6.2 角倍率 γ（reduced-angle と θ の両方）
reduced-angle の角成分倍率として
\[
\boxed{\gamma_u = D_s}
\]
を定義する。

角そのもの（θ）の倍率が必要な場合、\(u=n\theta\) より
\[
\boxed{\gamma_\theta = \frac{n_o}{n_i}D_s}
\]
を出力する。air→air なら \(\gamma_\theta=\gamma_u\)。

### 6.3 縦倍率 α と軸方向倍率
「縦倍率」の用語は曖昧なので、本実装では次を明示する：

- \[
\boxed{\alpha = \beta}
\]
（一般的な撮像で「倍率」と呼ぶもの）

- 軸方向倍率（longitudinal magnification）：
\[
\boxed{m_L = \beta^2\frac{n_i}{n_o}}
\]
を `longitudinal_mag` として出力する。

---

## 7. ニュートン公式（Newton relation）チェック

### 7.1 焦点位置の絶対座標 \(z_F, z_{F'}\)
カーディナル点で得た主平面と焦点距離から焦点を絶対化する。

- 前側主平面の絶対位置 \(z_H\)
- 後側主平面の絶対位置 \(z_{H'}\)
- 焦点距離 \(f\)（air→air なら \(f=f'=\mathrm{EFL}\)）

\[
\boxed{z_F = z_H - f}
\]
\[
\boxed{z_{F'} = z_{H'} + f}
\]

### 7.2 ニュートン距離 \(x, x'\) の定義（符号を固定）
ニュートン公式を
\[
\boxed{x\,x' = f^2}
\]
の形でチェックできるよう、距離の向きを固定する：

- 物体側距離（物体側へ正）：
\[
\boxed{x = z_F - z_o}
\]
- 像側距離（像側へ正）：
\[
\boxed{x' = z_i - z_{F'}}
\]

air→air・近軸結像であれば \(x x' \approx f^2\) が成立する。

### 7.3 運用規約
- `object_distance_mm is None`（無限遠）では Newtonチェックはスキップ（意味が薄い）
- 有限共役では `relerr`（相対誤差）を出し、実装の整合性検証に使う

---

## 8. `test1_2`（有限共役モード）の結果と妥当性解釈

### 8.1 実行条件（代表）
- `object_distance_mm = -500.0 mm`（reference基準）
- `image_mode = "paraxial"`（有限共役では \(B_s=0\) を解く）
- 像側媒質：air（\(n_i=1\)）
- 参照波長：report規約（通常中央波長）

### 8.2 出力（ユーザー提示の抜粋）
```text
--- Magnifications (Plan B) --- 
beta (lateral)        = -0.236944000
alpha (==beta)        = -0.236944000
gamma_u (u-mag)       = -4.220406504
gamma_theta (theta)   = -4.220406504
longitudinal_mag      = 0.056142459
focus_indicator_B (Bs)= -1.278976924e-13

--- Newton relation check ---     
z_o   = -500.000000 mm
z_i   = 142.926292 mm
z_F   = -77.955542 mm
z_F'  = 119.231679 mm
x     = 422.044458 mm
x'    = 23.694614 mm
x*x'  = 1.000018044e+04
f^2   = 1.000018044e+04
relerr= 7.276e-16
```

### 8.3 妥当性（光学的・数値的）評価

#### (1) \(B_s\) がほぼ 0 → 有限共役の合焦面が正しく解けている
`image_mode="paraxial"`（有限共役）では、実装は \(B_s=0\) から \(L_i\) を解いて像面を決める。  
出力の
- \[
B_s \approx -1.28\times 10^{-13}
\]
は **浮動小数点誤差レベルでゼロ**であり、パラキシャルの結像条件が機械精度で満たされている。

このとき初めて、\(\beta=A_s\) を「横倍率」として強く解釈できる（無限遠モードとは異なる）。

#### (2) \(\beta=-0.236944\) の符号と大きさ
- \(\beta<0\) は倒立像（実像）を示し、一般的な結像と整合する。
- 大きさ \(|\beta|\approx 0.237\) は、物体距離 500mm に対し像距離が 143mm 程度の系として自然にあり得る。

#### (3) 軸方向倍率 `longitudinal_mag` の整合性（内部検算）
空気→空気なら
\[
m_L = \beta^2
\]
である。出力を見ると
- \(\beta^2 \approx (0.236944)^2 \approx 0.05614\)
- `longitudinal_mag = 0.056142459`

となり、定義通りの整合が取れている。

#### (4) 角倍率 \(\gamma_u=D_s\) の解釈
`gamma_u` は reduced-angle の角成分 \(u=n\theta\) の倍率で
\[
\gamma_u = D_s
\]
である。有限共役では物体側・像側伝搬を含むため、\(|D_s|>1\) となること自体は不自然ではない。  
符号が負であることは、像形成に伴う向きの反転と整合する。

> 注意：\(\gamma\) は単独で直感判断しづらい。最重要は「合焦面（\(B_s\approx0\)）で、\(\beta\) と Newton が矛盾しない」ことであり、ここでは矛盾はない。

#### (5) Newton公式が機械精度で一致 → 定義・絶対座標化が一貫
定義より
\[
x = z_F - z_o,\qquad x' = z_i - z_{F'}
\]
なので
- \(x = 422.044458\) mm
- \(x' = 23.694614\) mm

が得られ、出力の
- \(x x' = 1.000018044\times 10^4\)
- \(f^2 = 1.000018044\times 10^4\)
- `relerr=7.276e-16`

は **倍精度の丸め限界レベルで一致**している。  
これは
- \(z_F, z_{F'}\) の絶対化
- \(z_o, z_i\) の絶対座標の扱い
- \(x,x'\) の符号規約
- \(f\)（EFL）
が相互に完全に整合している強い証拠である。

---

## 9. 実装上の注意（解釈の落とし穴）

1. **無限遠入力（`object_distance_mm=None`）のとき**  
   - 本仕様では \(L_o=0\)（\(T_o=I\)）とするため、  
     その場合 `beta=A_s` は有限共役の「横倍率」としての意味が弱い。  
   - 代わりに `B_s` は「角→像高」の変換係数として現れやすく、EFLスケールの値を取り得る。  
   - Newtonチェックはスキップする。

2. 有限共役の合焦は **パラキシャル（一次）**  
   - 収差込みの最良焦点や、実レイトレ（スポット図）の最小RMSとは一致しないことがある。  
   - ただし一次整合（B_s≈0・Newton一致）は、実装の正しさ確認として最重要。

3. レイトレーシング側（opticspy）は多くの場合「視野角ベース」で ray を生成するため、  
   有限共役で厳密に物体点像を評価するには「物体面（高さ）基準の ray 生成」など追加設計が必要になる。

---

## 10. 仕様の最小確認項目（テスト観点）

有限共役モード（例：`test1_2`）で以下が成立すること：

- `focus_indicator_B (Bs)` が数値誤差レベルで 0
- `alpha == beta`
- `longitudinal_mag == beta**2*(n_i/n_o)`（air→airなら beta^2）
- Newtonチェックで `relerr ~ 1e-12 以下`（理想は 1e-15 付近）

---

以上。
