# test1_1 / example1 における Aperture・瞳・倍率・BFL・EP/EX の実装解釈（統合版）

本書は、以下の質疑で説明した内容を **重複を整理して統合**し、`test1_1`（および `example1`）の現状実装に基づく解釈としてまとめたものです。

- (A) test1_1/example1 における stop / 有効径 / F数 / 入射瞳 / 出射瞳
- (B) stop面の有効径を定めずに入射瞳径をどう決めているか（EFL/EPD/FNO の意味と関係式）
- (C) 有効径が不要に見えても stop面が必要な理由
- (D) EP/EX の計算実装（opticspy と abcd_common/abcd_report の実装状況）

---

## 0. 全体像（結論の要約）

現状の `test1_1` / `example1` は、**「開口量はF#で与える」「開口位置はstop面で定める」**という簡略モデルで動いている。

- **開口量（明るさ）**：ユーザーが `FNO` を与える → パラキシャル `EFL` から `EPD = EFL/FNO` を決める  
  （stop面の物理穴径＝クリアアパーチャは指定していない）
- **開口位置（瞳の位置）**：`stop=True` を付けた面が **Aperture Stop** として扱われ、これを基準に `EP`（入口瞳位置）や `EX`（出口瞳位置）が決まる
- **倍率（β/α/γ）やニュートンの公式**：現状の実装では計算・出力していない
- **BFL（バックフォーカス）**：2種類の概念が混在し得るが、レポートでは  
  - `compute_report` が **パラキシャル BFL = -A/C** を出力  
  - opticspy の `BFL()` は **処方上の最後厚み（recipe）**を返す  
  両者の差が `Δz` として表示される

---

## 1. (A) stop / 有効径 / F数 / 入射瞳 / 出射瞳の「設定」状況（実装ベース）

### 1.1 stop（開口絞り面）
**設定されている。**

- `test1_1`（および example1 相当）では、処方の特定面に `stop=True` を付けることで stop 面を指定する。
- `build_opticspy_lens()` は `SurfaceSpec.stop` を `Lens.add_surface(... STO=True ...)` へ渡す。
- opticspy 側の `first_order_tools.EP()` / `EX()` は `surface.STO` を見て stop 面番号を決める。

**重要**：この時点では stop 面の「穴径（クリアアパーチャ）」は与えていない。与えているのは **どの面が絞りか（位置）**のみ。

---

### 1.2 有効径（開口径）と F数（FNO）
**FNO は明示的に設定され、EPD（入射瞳径）はそこから計算される。**

- `example1.py`：`New_Lens.FNO = 5` のように設定
- `test1_1.py`：`fno = 5.0` を `build_opticspy_lens(..., fno=fno)` で渡し、内部で `Lens.FNO = fno` に設定

opticspy の `Lens.refresh_paraxial()` が

- `EFL` をパラキシャル計算（後述）
- `EPD = EFL / FNO` を計算

という流れで **入口瞳径（EPD）を決める**。

**結論**：現状のモデルでは
- 物理 stop 口径（面の有効径）を指定しない
- 代わりに **FNO を“仕様”として与え**、そこから必要な入口瞳径 EPD を逆算している

---

### 1.3 入射瞳（Entrance Pupil）
現状で扱っている入射瞳関連の量は以下。

- **EPD**（Entrance Pupil Diameter）：`EPD = EFL/FNO` により決まる（開口量）
- **EP**（Entrance Pupil position）：stop 面位置と前群の部分系ABCDから計算（開口位置）

さらに、opticspy のレイトレーサは **EP と EPD を実際に使って**光線を生成する。

- レイ生成（概念）：入口瞳位置（EP）で、入口瞳径（EPD）内の点を選んで光線を発射する  
  → そのため EP を定める stop 面が必要（後述）

---

### 1.4 出射瞳（Exit Pupil）
- **EX**（Exit pupil position）は `first_order_tools.EX()` により計算できる（stop 後ろ側部分系ABCDに依存）
- ただし、opticspy の標準 `Lens.refresh_paraxial()` は EP は保持するが、EX を Lens に保存してレイ生成に使う設計ではない（※比較ログ等で呼び出して確認はできる）

---

## 2. (B) stop面の有効径を定めずに入射瞳径をどう決めるのか（EFL/EPD/FNO）

### 2.1 用語の意味

- **EFL（Effective Focal Length）**  
  近軸（パラキシャル）での有効焦点距離。reduced-angle ABCD の `C` 成分から
  \[
  \mathrm{EFL}=f'=-\frac{1}{C}
  \]
- **EPD（Entrance Pupil Diameter）**  
  物体側から見た aperture stop の像（入口瞳）の直径。  
  重要なのは「stop 面そのものの穴径」ではなく、前群によって見え方（倍率）が変わる **“見かけの開口”**。
- **FNO（F-number）**  
  明るさの指標で、（空気中・無限遠物体の近軸定義として）
  \[
  \mathrm{F\#}=\frac{f'}{D_{EP}}
  \]
  と定義される。

### 2.2 なぜ `EPD = EFL / FNO` が成り立つか
上の定義式
\[
\mathrm{F\#}=\frac{f'}{D_{EP}}
\]
を入口瞳径 \(D_{EP}\) について解くと、
\[
D_{EP}=\frac{f'}{\mathrm{F\#}}
\]
すなわち
\[
\mathrm{EPD}=\frac{\mathrm{EFL}}{\mathrm{FNO}}
\]
となる（定義から直接出る）。

### 2.3 実装としての解釈
現状実装では、stop 面の物理口径が与えられていないため、
- `FNO`（明るさ仕様）を入力
- `EFL`（パラキシャル計算の結果）を出す
- その2つから `EPD`（入口瞳径）を **逆算で決める**

という「設計仕様主導」の簡略モデルになっている。

> 物理的には本来  
> **stop 口径 →（前群の倍率）→ EPD → FNO**  
> と決まることが多いが、現状は逆方向で固定している。

---

## 3. (C) 有効径が不要に見えても stop 面が必要な理由

### 3.1 stop 面が決めるのは「径」ではなく「位置」
stop 面の穴径（クリアアパーチャ）を使わなくても、stop 面は

- **入口瞳位置 EP**
- **出口瞳位置 EX**

を決めるために必要である。これらは「絞りが系のどこにあるか」で変わる（同じ EPD でも stop 位置で EP/EX が大きく変わる）。

### 3.2 レイ束生成に EP が必要
opticspy のレイトレーサは、入口瞳径 `EPD` だけでなく、**入口瞳位置 `EP`**を使って光線を生成する。

- 視野角（field angle）をもつ主光線を
- 入口瞳面（EP位置）で定義し
- その入口瞳内（±EPD/2）の点から ray を発射する

したがって stop 面が無いと
- EP が計算できず
- レイ束の基準面が定まらない
という問題が起きる。

**結論**：現状の簡略モデルにおいて stop 面は  
「物理口径を決めるため」ではなく  
**「瞳位置（EP/EX）とレイ束定義のため」**に必要。

---

## 4. (D) EP/EX はどう計算されているか（opticspy と abcd_* の実装）

### 4.1 opticspy の EP（Entrance Pupil position）
`opticspy.ray_tracing.first_order_tools.EP(Lens)` の概略：

1. stop 面番号 `n` を探索（`surface.STO == True`）
2. stop が surface2 の場合：`EP = 0`
3. stop 直前の thickness を取得：`t_stop = thickness(stop-1)`
4. 部分系 ABCD を構築：`start_surface=2`, `end_surface=n-1` → `A,B,C,D`
5. opticspy 実装式で EP を算出：
   - `phi = -C`
   - `P  = (D-1)/C`
   - `Pp = (1-A)/C`
   - `lp = t_stop - Pp`
   - `l  = 1/(1/lp - phi)`
   - `EP = l + P`

> 解釈：stop を前群で見たときの像位置（入口瞳位置）をパラキシャルに求める。

### 4.2 opticspy の EX（Exit Pupil position）
`first_order_tools.EX(Lens)` の概略：

1. stop 面番号 `n` を探索
2. stop が最後の実面側にある場合：`EX = 0`（実装規約）
3. stop 直後の thickness を取得：`t_stop = thickness(stop)`
4. 部分系 ABCD を構築：`start=n+1`, `end=last_refracting` → `A,B,C,D`
5. opticspy 実装式で EX を算出：
   - `phi = -C`
   - `P  = (D-1)/C`
   - `Pp = (1-A)/C`
   - `l  = -(t_stop + P)`
   - `lp = 1/(1/l + phi)`
   - `EX = lp + Pp`

> 解釈：stop を後群で見たときの像位置（出口瞳位置）をパラキシャルに求める。

---

### 4.3 自作 `abcd_common.py` / `abcd_report.py` の実装状況

- `abcd_common.py`  
  **EP/EX は実装していない**。役割は「ABCD → カーディナル点などの純数学」に限定している。

- `abcd_report.py`  
  **EP/EX を実装している（opticspy と同じ式）**。  
  代表的に以下の関数で再現している：
  - `entrance_pupil_position_from_prescription(...)`
  - `exit_pupil_position_from_prescription(...)`
  - `first_order_like_opticspy(cfg, ...)`（内部で EP/EX を呼ぶ）

> したがって「自分の実装に EP/EX が無い」のではなく、  
> **abcd_common には無いが、abcd_report にはある**のが現状。

---

## 5. (A-2) 倍率（β/α/γ）とニュートンの公式の扱い

現状の `test1_1` / `example1`（および opticspy 的利用範囲）では：

- **横倍率 β、縦倍率 α、角倍率 γ** を計算・出力していない
- **ニュートンの公式**（\(x x' = f^2\) 等）も評価していない

理由（実装観点）：
- opticspy の first-order が主に EFL/EP/EX などにフォーカスしており、共役系（有限物体距離）まで一般化した倍率レポート設計ではない
- `object_position` は無限遠近似の固定値で運用されることが多く、倍率群を体系的に出すには「距離の基準（主平面）」「像面位置のsolve」などを追加で定義する必要がある

---

## 6. (A-3) バックフォーカス（BFL）は出力されているか

**出力されている。ただし2種類ある。**

### 6.1 opticspy `BFL()` の意味（recipe）
opticspy `first_order_tools.BFL()` は ABCD 由来ではなく、**処方の最後厚み**（像面直前面の thickness）を返す。  
本書では **`BFL_recipe`** と呼ぶ。

### 6.2 `compute_report` の BFL（paraxial）
`compute_report`（ABCDレポート）側は、ABCDから
\[
\mathrm{BFL}_{\mathrm{parax}} = -A/C
\]
を計算し、これを BFL として出力する。

### 6.3 `Δz` の意味
- recipe 像面位置（処方で定めた像面）
- paraxial 焦点位置（ABCD由来の焦点）

の差を
\[
\Delta z = z_{image\,(recipe)} - (z_{end} + \mathrm{BFL}_{\mathrm{parax}})
\]
として出すと、これは
- 「像面がパラキシャル焦点からどれだけ外れているか（デフォーカス量）」
の指標になる。

---

## 7. まとめ（現状実装の検討結果）

- stop 面：**面番号で指定される（位置の指定）**
- 有効径（入口瞳径 EPD）：**FNO を仕様として与え、EFL から逆算で決まる**  
  （物理 stop 口径は未設定）
- 入口瞳位置 EP：**stop 面と前群部分系ABCDで計算され、レイ生成に使用される**
- 出口瞳位置 EX：**stop 面と後群部分系ABCDで計算できる（比較で使用）**
- 倍率（β/α/γ）・ニュートン公式：**現状は未計算・未出力**
- BFL：**recipe（処方厚み）と paraxial（-A/C）の両概念があり、両者差はΔzとして解釈できる**

---

以上。
