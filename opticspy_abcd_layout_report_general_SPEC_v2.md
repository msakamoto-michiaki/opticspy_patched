
# opticspy_abcd_layout_report_general.py 仕様書

作成日: 2026-01-25

この文書は、`opticspy_abcd_layout_report_general.py` の**仕様**（設計意図・入出力・数式・実装上の前提）をまとめたものです。  
特に、**ABCD行列（パラキシャル行列）計算部**の仕様を詳細に記述します。加えて、本スクリプトが利用している `opticspy` モジュール（アップロードされた `opticspy-master.zip` 由来）について、利用箇所を中心に可能な限り詳しく説明します。

---

## 1. 目的と全体像

`opticspy_abcd_layout_report_general.py` は、任意の光学系処方（面データ）を入力として：

1. **ABCD行列（パラキシャル行列）**を計算  
2. **有効焦点距離 f'（EFL）**、**主平面 H / H'**、**後焦点距離 BFL**等を計算  
3. **処方式の像面**（指定された像面位置）と **ABCDから得られるパラキシャル後焦点面** を比較  
4. （任意）`opticspy` の `trace.trace_draw_ray()` と `draw.draw_system()` を用いて **レイアウト図（レンズ断面＋光線）**をPNG出力

を一括で実施します。

---

## 2. 依存関係

### 2.1 Pythonパッケージ
- `numpy`
- `matplotlib`（描画保存用。GUI不要にするため Agg backend を使用）
- `dataclasses`（設定・処方データ構造）
- `typing`

### 2.2 opticspy（ローカル版）
- 本スクリプトは `OPTICSPY_ROOT`（環境変数）または既定パスを `sys.path` に追加して `opticspy` を import します。  
- 既定のパス:
  - `"/mnt/data/opticspy_work/opticspy-master"`

> 注意: 一部の `opticspy` スナップショットでは `unwrap` という補助モジュールが import される前提があるため、本スクリプトでは `import unwrap` を try/except で安全に扱っています（無くても落ちないようにする）。

---

## 3. 入力データ仕様

### 3.1 SurfaceSpec（面データ）
`SurfaceSpec` は 1面ぶんの処方を表すデータクラスです。

| フィールド | 型 | 意味 |
|---|---:|---|
| `num` | int | 面番号（1,2,3,... の連番を想定） |
| `R` | float | 曲率半径 [mm]。非常に大きい値は平面近似（∞）として扱う |
| `t` | float | 面 `num` から次面頂点までの距離（厚み） [mm] |
| `glass` | str | **その面の直後の媒質**（例: `"air"`, `"S-BSM18_ohara"`） |
| `stop` | bool | 絞り面（STO）フラグ。`opticspy` に渡す際は `STO=True` |

**コンストラクタ引数の順序（重要）**  
`SurfaceSpec(num, R, t, glass, stop=False)` の順です。

- `R` が **radius（曲率半径）**
- `t` が **thickness（次面までの距離）**

例：  
`SurfaceSpec(1, 10000000.0, 1000000.0, "air", False)` は  
「面1：半径=1e7 mm、次面まで厚み=1e6 mm、直後媒質=air、絞りでない」を意味します。


**重要な約束:**  
- `glass` は **面の直後の媒質**です。  
  例）面2がガラスに入る面で、面2直後がガラスなら `surface2.glass="S-BSM18_ohara"`。

---

## 4. 座標系・パラキシャルレイベクトルの定義

本スクリプトは、レイの状態を

\[
\mathbf{r} = \begin{bmatrix} y \\ \theta \end{bmatrix}
\]

で表します。

- `y` : 光軸からの高さ [mm]  
- `θ` : 光線の傾き（小角近似）[rad]  
- 光は **+z方向（左→右）**に進むとします。

この定義により、伝搬と屈折の行列は以下の形になります。

---

## 5. ABCD 行列計算仕様（重要）

### 5.1 計算対象範囲（start_surface / end_surface）
`ReportConfig` の

- `start_surface`（既定 2）
- `end_surface`（既定 8）

で、ABCD を計算する範囲を指定します。

**計算される行列 `M` の意味**  
- `M` は、「`start_surface` での屈折から始めて、`end_surface` の屈折を適用した **直後**」までの系行列です。  
- したがって `end_surface` の次の距離（像面までの伝搬）は `M` に含まれません（必要なら別途平行移動を前置して `M_to_img` を作ります）。

---

### 5.2 平行移動（Translation）行列

距離 `t` の空間伝搬（媒質の屈折率によらない、θを用いる定義）として：

\[
T(t) =
\begin{bmatrix}
1 & t \\
0 & 1
\end{bmatrix}
\]

- これは **y_out = y_in + t * theta_in** を表します。

---

### 5.3 球面屈折（Refraction）行列

曲率半径 `R` の球面で、左側屈折率 `n1` → 右側屈折率 `n2` の屈折を

\[
R(R,n_1,n_2)=
\begin{bmatrix}
1 & 0 \\
\frac{(n_1-n_2)}{n_2 R} & \frac{n_1}{n_2}
\end{bmatrix}
\]

で表します。

- 実装では曲率 `c = 1/R` を用い、`|R| > 1e12` のとき平面（`c=0`）として扱います。
- これは小角近似における  
  **theta_out = (n1/n2) * theta_in + ((n1-n2)/(n2*R)) * y_in**  
  を表現します。

---

### 5.4 行列合成順序（重要）
本スクリプトは、`start_surface` から `end_surface` まで

1. **面 i で屈折（Refraction）**  
2. （i < end_surface のとき）**厚み t_i だけ伝搬（Translation）**

を繰り返します。

合成は左から作用する形で実装されています（行列を左から掛けて更新）：

- `M = R_i @ M`
- `M = T(t_i) @ M`

最終的に

\[
\mathbf{r}_{out} = M\,\mathbf{r}_{in}
\]

となります。

---

### 5.5 屈折率の取得（opticspy glass_funcs）
屈折率は `opticspy.ray_tracing.glass_funcs.glass2indexlist()` を利用して取得します。

- 入力: `wavelengths_nm`（nmリスト）とガラス名
- 出力: 各波長に対する屈折率のリスト

本スクリプトは **「波長リストの中央要素（middle index）」**の屈折率を採用します。  
例）`[587.6, 656.3, 486.1]` の場合、長さ3なので中央は index=1 → **656.3 nm** になります。

> 注意（重要）  
> 以前の Example1 計算では「nd=587.6 nm」を意図していましたが、  
> `opticspy` の多くの内部関数が「middle wavelength を代表波長として使う」実装になっているため、  
> この汎用スクリプトも同じ規約（middle-wavelength）に合わせています。  
> **nd=587.6nm を必ず使いたい場合**は、波長リストを `[486.1, 587.6, 656.3]` のように並べて中央を 587.6nm にするか、  
> `get_refractive_index_nm()` を「587.6nm固定」に書き換えてください。

---

### 5.6 像面までの行列（M_to_img）
`image_surface` が指定されている場合、`end_surface` から `image_surface` までの距離 `dz` を計算し、

\[
M_{to\_img} = T(dz)\,M
\]

を作って表示します。

- `dz = z(image_surface) - z(end_surface)`  
- `z()` の定義は次節。

---

## 6. 絶対座標 z の定義（reference_surface）

本スクリプトは **頂点座標の累積和**により `z(surface)` を定義します。

- `reference_surface` の頂点を `z=0` とする  
- 以降、処方の厚み `t_i` を累積して各面頂点の z を得る

これにより

- `z_end = z(end_surface)`
- `z_img_prescribed = z(image_surface)`（指定時）

などを得ます。

---

## 7. 主平面・焦点距離の計算（air→air）

ABCD 行列

\[
M=
\begin{bmatrix}
A & B\\
C & D
\end{bmatrix}
\]

に対して（入射側・出射側とも空気を仮定）：

- **有効焦点距離（像側）**
  \[
  f' = -\frac{1}{C}
  \]

- **主平面（物側）位置**（reference_surface頂点からの距離）
  \[
  h = \frac{D-1}{C}
  \]

- **主平面（像側）位置**（end_surface頂点から左向き距離）
  \[
  h' = \frac{A-1}{C}
  \]

- **後焦点距離（BFL）**（end_surface頂点から右向き距離）
  \[
  \mathrm{BFL} = -\frac{A}{C}
  \]

本スクリプトの絶対座標では

- `z(H)  = h`（reference_surfaceの z=0 を基準）
- `z(H') = z_end - h'`
- `z(back focus) = z_end + BFL`

となります。

---

## 8. 像面比較（処方像面 vs ABCD後焦点面）

像面の指定は2通りです。

### 8.1 image_surface による指定（推奨）
- `image_surface` を指定すると、処方から `z(image_surface)` を取り、処方像面とします。

### 8.2 image_z_abs による直接指定
- 絶対座標 `z` を直接与える方法です（例: 外部最適化で決めた像面位置など）。
- 指定された場合、`image_surface` より優先されます。

### 8.3 比較量
- `z_img_abcd = z_end + BFL`
- `difference = z_img_abcd - z_img_prescribed`

差が 0 でない場合は、処方の像面がパラキシャル後焦点面に一致していないことを意味します。

---

## 9. opticspy によるレイアウト図出力

### 9.1 利用している opticspy の主モジュール
本スクリプトは次を利用します。

- `opticspy.ray_tracing.lens`
  - `lens.Lens`：レンズ系オブジェクト
  - `Lens.add_surface()`：面追加
  - `Lens.add_field_YAN()`：視野角（YAN）追加
  - `Lens.refresh_paraxial()`：パラキシャル量（EFL, 瞳位置等）計算

- `opticspy.ray_tracing.trace`
  - `trace.trace_draw_ray(Lens)`：レイアウト描画用の光線追跡（複数視野・複数種 ray）

- `opticspy.ray_tracing.draw`
  - `draw.draw_system(Lens)`：レンズ断面＋追跡した光線を matplotlib で描画（通常は `plt.show()`）

- `opticspy.ray_tracing.glass_funcs`
  - `glass2indexlist(wavelength_list, glass_name)`：波長ごとの屈折率を返す

### 9.2 opticspy の描画フロー（本スクリプトでの扱い）
通常 `draw.draw_system()` は `plt.show()` を呼びます。  
本スクリプトは GUI 依存を避けるため、

- `matplotlib` の backend を `"Agg"` に設定
- `plt.show` を一時的に差し替えて `plt.savefig()` を実行

という方法で PNG 保存します。

### 9.3 opticspy 側の注意点（このスナップショット固有の癖）
- `Lens.surface_list` が **クラス変数的に共有される**実装になっているスナップショットがあり、  
  連続実行で前回の面が残ることがあります。
  - 本スクリプトでは安全のため `L.surface_list = []` で必ず初期化します。

- `refresh_paraxial()` 実行前に `Lens.wavelength_list` が設定されていないと、ガラス屈折率計算で例外になる場合があります。
  - 本スクリプトは必ず `L.wavelength_list = wavelengths_nm` を設定してから `refresh_paraxial()` を呼びます。

---

## 10. 環境変数・出力

### 10.1 OPTICSPY_ROOT
- `opticspy` のルートディレクトリ（`opticspy/` パッケージを含むフォルダ）を指定。
- 指定がない場合、既定は `"/mnt/data/opticspy_work/opticspy-master"`。

### 10.2 OUT_PNG
- `main()` の Example1 実行時に保存する PNG パスを指定できます。
- 例: `OUT_PNG=/content/example1.png python opticspy_abcd_layout_report_general.py`

---

## 11. 拡張・カスタマイズ指針

- **nd固定にしたい**  
  - `get_refractive_index_nm()` を 587.6nm のみに変更、あるいは波長リストを中央が587.6になるよう並べ替える。

- **像面をパラキシャル後焦点に自動一致させたい**  
  - `compute_report()` で `z_img_prescribed = z_img_abcd` を設定するオプションを追加する。

- **媒質が空気以外（入射側・出射側）**  
  - `cardinals_air_air()` は air→air 前提なので、一般式（媒質差あり）に差し替える必要がある。

---

## 付録A: Example1 用 config（参照）
スクリプト内 `example1_config()` が Example1 の実装例です。  
（`SurfaceSpec` / `ReportConfig` を組み立てて `run_report_and_optional_plot(cfg)` へ渡すだけ）

---

## 付録B: 既知の落とし穴

1. **像面差が0でない**  
   - それは計算ミスではなく、処方像面位置がパラキシャル焦点と一致していない可能性があります。

2. **保存パスが存在しない**  
   - Colab 等で `/mnt/data` が存在しない場合は `OUT_PNG` を `/content/...` にするのが安全です。

---

以上。
