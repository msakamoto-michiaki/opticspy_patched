# `abcd_common.py` + `abcd_report.py` 仕様書（ABCD/カーディナル点/first-order互換）

本書は、ABCD 行列の計算と、カーディナル点・first-order 指標の出力を担う

- `optics/abcd_common.py`
- `optics/abcd_report.py`

の仕様をまとめる。

---

## 1. 設計方針（役割分担）

### 1.1 `abcd_common.py`（純数学層）
- **ABCD 行列から導出できる量**のみを扱う
- `SurfaceSpec` や STOP 面、厚み総和など「レンズ処方依存」のロジックは持たない
- 再利用性を最優先にする

### 1.2 `abcd_report.py`（アプリ層）
- `SurfaceSpec` 列と `ReportConfig` を用いて ABCD を直接積算する
- opticspy `first_order_tools` 相当の指標を **同じ意味・同じ式**で算出し、比較検証を可能にする
- print/CLI は持たず、値を返す（表示は test 側）

---

## 2. `abcd_common.py` 仕様

### 2.1 対象とする状態ベクトル
本プロジェクトは reduced-angle 形式を採用する：

- 状態：\([y, u]^T\)
- 定義：\(u = n\theta\)（媒質屈折率 n と光線角 \(\theta\) の積）

### 2.2 カーディナル点計算（代表）
関数例：`cardinals_air_air_full(A,B,C,D)`

- 入力：ABCD 行列成分
- 出力：EFL、主平面位置、BFL などのカーディナル点情報

典型式：
- EFL：\(f'=-1/C\)
- paraxial BFL：\(\mathrm{BFL}=-A/C\)
- 主平面などは A,B,C,D から導出

> `abcd_common.py` は原則として「行列の成分 → 物理量」変換に限定する。

---

## 3. `abcd_report.py` 仕様

### 3.1 ABCD 直接積算：`compute_abcd_from_prescription(...)`

#### 入力
- `prescription: List[SurfaceSpec]`
- `wavelength_nm: float`（参照波長：通常は中間波長）
- `start_surface: int`
- `end_surface: int`
- `opticspy_root: Optional[str]`（屈折率取得用）

#### 屈折率
- ガラス名 → `opticspy.ray_tracing.glass_funcs.glass2indexlist()` を用いて屈折率を得る
- 参照波長（通常は `wavelengths_nm` の中央要素）の n を採用し、opticspy と整合させる

#### 伝搬行列
厚み `t`、媒質 `n` に対して：
\[
T = \begin{pmatrix}1 & t/n \\ 0 & 1\end{pmatrix}
\]

#### 屈折行列
曲率半径 `R`、入射側 `n1`、出射側 `n2` に対して：
\[
R = \begin{pmatrix}1 & 0 \\ -(n_2-n_1)/R & 1\end{pmatrix}
\]

#### 積算順序
`start_surface..end_surface` の範囲で、
- 面で屈折 → 面後厚みで伝搬
を順に掛け合わせる（opticspyの reduced-angle 定義と整合すること）。

---

### 3.2 レポート生成：`compute_report(cfg)`
`ReportConfig` に基づき、参照波長（通常 `wavelengths_nm` の中間値）で

- ABCD
- カーディナル点（EFL、主平面 H/H'、BFL）
- 像面位置のチェック（recipe vs paraxial）

などを計算し、表示用の構造（dict/dataclass）として返す。

> 表示（print）は test 側（`# Extract/Print` ブロック）に置く。

#### 像面チェックの意味（重要）
- recipe 像面位置：処方の最後厚み（像面直前面の thickness）で決まる
- paraxial 焦点位置：ABCD から得た \(\mathrm{BFL}_{\mathrm{parax}}=-A/C\)
- 差分 \(\Delta z\) は「像面がパラキシャル焦点からどれだけ外れているか（デフォーカス量）」の指標

---

### 3.3 opticspy互換 first-order：`first_order_like_opticspy(cfg, object_distance=...)`

#### 目的
opticspy の `first_order_tools` と **同じ意味・同じ式**で値を算出し、テストで比較可能にする。

#### 返す量（例）
- `efl_full`：\(f'=-1/C\)
- `bfl_paraxial`：\(-A/C\)
- `image_position`：\(-A/C + f^2/z\)（opticspy実装準拠）
- `bfl_recipe`：像面直前厚み（opticspy `BFL()` と同義）
- `ep`：入口瞳位置（STOP面＋部分系ABCD＋opticspy式）
- `ex`：出口瞳位置（STOP面＋部分系ABCD＋opticspy式）

#### 注意（BFLの2種類）
- opticspy `BFL()` は **処方の最後厚み**（`bfl_recipe`）
- ABCD由来の BFL は **パラキシャル焦点距離**（`bfl_paraxial`）

両者は一致するとは限らず、その差はデフォーカス指標として利用できる。

---

### 3.4 厚み総和：`oal_from_prescription(prescription, start, end)`
opticspy `OAL(start,end)` と同義：

\[
\mathrm{OAL} = \sum_{i=start}^{end-1} t_i
\]

---

## 4. テストでの比較（`test*_*.py`）

### 4.1 opticspy側の呼び出し
opticspy first-order は内部で `print()` することがあるため、`_quiet_call` で stdout を抑制して取得する。

### 4.2 ABCD direct 側
`abcd_report.py` 側は print せず、戻り値を test 側が表示する。

### 4.3 一致が期待される量
- `EFY`（full / 部分系）
- `image_position`
- `EP/EX`
- `OAL`
- `BFL_recipe`（処方厚み）

---

以上。
