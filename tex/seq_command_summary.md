# ex_CodeV の `.seq` 解析メモ（仕様書ドラフト用）

> 目的  
> このドキュメントは、当該リポジトリの `ex_CodeV/` 配下にある CODE V 形式 `.seq` を **`test1_1` 形式（`SurfaceSpec` / `ReportConfig`）へ変換**し、将来的に **相互変換（.seq ↔ prescription/config）** を実装するための仕様メモです。  
> ここでいう「反映される/無視される」は、**opticspy の簡易パーサ `codev.readseq()` が解釈するかどうか**の観点で整理しています。

---

## 1. 重要な前提（opticspy の `.seq` は「サブセット」）

CODE V の `.seq` には多様なコマンドがありますが、本プロジェクトで利用している opticspy の `codev.readseq()` は、以下のような **限定的サブセット**のみを解釈する実装になっています。

- **解釈（Lens に反映）するコマンド**  
  `TITLE`, `WL`, `EPD`, `XAN`, `YAN`, `FNO`, `NA`, `SO`, `S`, `SI`, `STO`

- **それ以外は原則として無視**（ただし、相互変換のために “メタデータとして保持” するのが望ましい）

---

## 2. `.seq` → `SurfaceSpec` 変換規約（面の対応）

### 2.1 面行（SO/S/SI）

`.seq` の面行は先頭トークンが以下のいずれか：

- `SO` : Object surface（物体面）
- `S`  : 通常の面
- `SI` : Image surface（像面）

opticspy の簡易パーサでは、これらは **いずれも「面を1枚追加する」行**として扱われます（タグの意味差は主に人間のため）。

**基本フォーマット（サブセット）**
```
SO  R  t  [glass]
S   R  t  [glass]
SI  R  t  [glass]
```

対応（`SurfaceSpec(num, R, t, glass, stop)`）：

- `num` : 読み込んだ順に 1,2,3,...（自動採番）
- `R`   : 曲率半径
- `t`   : その面から次面までの厚み/間隔
- `glass` : ガラス名。省略時は `"air"` とする
- `stop`  : `STO` により付与（後述）

### 2.2 STOP 指定（STO）

- `STO` 行は **直前の面**に STOP フラグを付与する
- `SurfaceSpec(..., stop=True)` となる

> 注意：`STO` は “O（オー）” であり、`ST0`（ゼロ）ではない。

### 2.3 平面の扱い（R=0）

CODE V の慣習では `R=0` が平面を表しますが、opticspy 側は `R=0` を巨大半径に置換して平面近似する実装が多いです。  
本プロジェクト側（`test1_1` 形式）でも、同様に

- `R==0` → `R=10000000.0`（例）

として扱うのが互換的です。

---

## 3. `.seq` → `ReportConfig` / 描画条件の対応

### 3.1 ReportConfig に落とす情報（ABCD/主平面レポート向け）

- `wavelengths_nm` : `WL ...` の値（ただし **単位の統一方針**が必要。nm/µmのどちらで書かれているかに注意）
- `prescription`   : 2章の規約で生成した `SurfaceSpec` の配列
- `reference_surface` : 通常 `2`（`SO` を z=0 にしないで、最初の実面を基準にする）
- `start_surface`  : 通常 `2`（`SO` を除外して第1実面から）
- `image_surface`  : 最終面（`SI` の面番号）
- `end_surface`    : 通常 `image_surface - 1`（像面直前まで）

> `ReportConfig` は「ABCDレポート用」に最小化しておき、描画/解析用の条件は別構造（`SeqConditions` 等）に保持するのが推奨。

### 3.2 描画・スポット図に必要な条件（test1_1 側で使用）

- 視野角：`YAN ...` / `XAN ...`
  - opticspy では `.seq` を読んだ時点で Lens に field が登録され、解析は **フィールド番号（1,2,3...）**で指定することが多い
  - `build_opticspy_lens()` 方式（処方から Lens 再構築）を使う場合は、`field_angles_deg = YAN` をそのまま渡すのが自然

- `FNO`：
  - `.seq` に `FNO` があればそれを使えるが、`example3/4` ではスクリプト側で `Lens.FNO = ...` を上書きする実装になっている場合がある
  - `.seq` に `NAO`（後述）しか無いケースもあるため、まずは `fno` を **外部指定可能**にする設計が安全

---

## 4. ex_CodeV の `.seq` に登場するコマンド一覧（分類）

ここでは `ex_CodeV/` 配下の `.seq` で見られるコマンド（先頭キーワード、または `;` で連結されるコマンド）を、  
「opticspy の簡易パーサで反映されるか」を軸に分類します。

### 4.1 opticspy が解釈して反映する（Lens に入る）

- `TITLE` : レンズ名
- `WL`    : 波長リスト
- `EPD`   : Entrance Pupil Diameter
- `XAN` / `YAN` : 視野角リスト
- `FNO`   : F-number
- `NA`    : Numerical Aperture（※ただし `.seq` に `NAO` が出る場合は別扱い）
- `SO` / `S` / `SI` : 面定義（R, t, glass）
- `STO`   : stop 面指定（直前の面）

### 4.2 仕様上「保持したい」が、簡易パーサでは無視される（メタデータ）

#### A) 条件・重み・単位・ビネッティング等

- `DIM M` : 単位系（mm 等）
- `INI ...` : 初期化/環境設定（例：`INI 'ORA'`）
- `REF ...` : 参照波長指定（例：W2 を基準、等）
- `WTW ...` : 波長重み
- `WTF ...` : フィールド重み
- `VUX`, `VUY`, `VLX`, `VLY` : ビネッティング係数（フィールドごとのクリップ等）
- `NAO ...` : NA 系の別コマンド（簡易パーサが `NA` のみ対応の場合に無視される）
- `CA` : クリアアパーチャ/開口チェック関連の設定として用いられる例がある（本プロジェクトでは未反映）
- `RED ...` : 拘束/ソルブ系コマンドとして出現する例（本プロジェクトでは未反映）

#### B) 面に付随するコマンド（最適化・開口など）

これらは通常、面行（`SO/S/SI`）の直後に並びます。

- `CCY ...` : 曲率に関する最適化/拘束系
- `THC ...` : 厚みに関する最適化/拘束系
- `CIR ...` : 開口（semi-diameter）指定
- `CIR EDG ...` : エッジ側開口/外形寄り指定のバリエーション
- `EDG ...` : エッジ関連（`CIR EDG` の形で現れることが多い）
- `CUY ...` など : ソルブ/制約系として現れることがある

#### C) 実行・出力・後処理

- `PIM` : 像面距離の solve/パラキシャル像面に関連する指定として現れることがある
- `GO`  : 実行（run）
- `DER VAL ...` : 出力（導関数/評価値）の列挙
- `RDM;LEN ...` : `;` 連結されたコマンド（ヘッダ/メタ用途）

---

## 5. 相互変換（往復）を壊さないための保持戦略

`SurfaceSpec/ReportConfig` に無理に詰め込まず、次の2種類に分けて保存するのが推奨です。

### 5.1 グローバルコマンド（面に紐づかない行）

例：`DIM`, `INI`, `WL`, `XAN`, `YAN`, `WTW`, `WTF`, `VUX/VUY/VLX/VLY`, `NAO`, `PIM`, `GO`, `DER...`, `RDM;LEN...`

- `SeqConditions.global_cmds: list[str]` のように **原文のまま保存**
- `.seq` 書き戻し時に順序を保って再出力できるようにする

### 5.2 面ごとの付随コマンド（面行の直後の行）

例：`CCY`, `THC`, `CIR`, `CIR EDG`, `CUY ...`

- `surface_cmds[num]: list[str]` のように **面番号ごとのリスト**として保持
- `.seq` 書き戻し時に「面行 → 付随行群 → 次の面行 …」で再構成する

---

## 6. パーサ実装時の注意点（microscope.seq で重要）

### 6.1 行継続 `&`

`microscope.seq` では `VUX/VLX/VUY/VLY` が `&` で改行継続になり、次行が数値だけになる形式があります。

実装では：

- 行末が `&` の場合、**次行を連結して1行として処理**する

を必須にすること。

### 6.2 `;` 連結コマンド

`RDM;LEN ...` のように、1行に `;` で複数コマンドが書かれることがあります。

- 仕様としては「先頭から `;` で分割し、**それぞれを独立コマンド**として扱う」
- ただし “書き戻し時に同じ形式で戻す” を重視するなら、原文行のまま保持する選択もあり

---

## 7. 変換 API の最小案（次ステップ向け）

- `parse_seq(path) -> (prescription, cond, surface_cmds, global_cmds)`
- `to_report_config(prescription, cond) -> ReportConfig`
- `write_seq(path, prescription, cond, surface_cmds, global_cmds)`

この形にすると、

- ABCD用途（`ReportConfig`）と
- 描画用途（`cond.yan_deg`, `cond.fno`, EPD等）と
- 往復保持（`surface_cmds/global_cmds`）

が衝突せずに実装できます。

---

## 付記：用語

- **prescription**：面列（曲率半径R、厚みt、ガラス、stop）
- **条件**：波長、視野角、入口瞳径、FNO/NA など
- **メタデータ**：最適化のvary/constraint、出力指示、単位設定、実行指示など
