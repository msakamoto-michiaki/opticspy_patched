# `seq_convert.py` + `yaml_io.py` 仕様書（.seq ⇄ test1_1 相互変換 / YAML IO）

本書は、`.seq`（CODE V 風サブセット）と `test1_1` 形式（`SurfaceSpec` / `ReportConfig`）の相互変換を担う

- `optics/seq_convert.py`
- `optics/yaml_io.py`

の仕様をまとめる。

> 設計方針（最重要）
> - `SurfaceSpec` / `ReportConfig` は **汚さない**（`.seq` 固有コマンドの保持は別構造へ）
> - `.seq` のうち **面に紐づかない行**は `SeqConditions` に保持し、YAML で保存・復元できる
> - 相互変換は「行単位の完全一致」ではなく「**意味的同値（処方・主要条件）**」を保証する（writer は正規化する）

---

## 1. データモデル

### 1.1 `SeqDocument`
`.seq` 1本分を表す集約オブジェクト。

- `prescription: List[SurfaceSpec]`
- `conditions: SeqConditions`

### 1.2 `SeqConditions`
`.seq` に現れる “面以外” の情報を保持する（`SurfaceSpec`/`ReportConfig` に入れない）。

推奨フィールド（実装により多少増減してよい）：

- `title: str`
- `dim: Optional[str]`（例：`DIM M` の `M`）
- `wavelengths: List[float]`（`WL ...` の値列）
- `xan_deg: List[float]`（`XAN ...`）
- `yan_deg: List[float]`（`YAN ...`）
- `epd: Optional[float]`（`EPD ...`）
- `fno: Optional[float]`（`FNO ...`）
- `na: Optional[float]`（`NA ...`）
- `nao: Optional[float]`（`NAO ...` のような派生）
- `raw_cmds: List[str]`  
  面に紐づかない行（例：`INI ...`, `WTW ...`, `WTF ...`, `CA`, `PIM`, `GO`, `RDM`, `LEN`, `DER ...` 等）を**出現順**で保持
- `surface_cmds: Dict[int, List[str]]`  
  面直後の補助行（例：`CCY`, `THC`, `CIR`, `CIR EDG`, `EDG`, `CUY ...` 等）を**面番号に紐付けて**保持
- `plane_surfaces: List[int]`  
  入力 `.seq` で `R=0`（平面）だった面番号を記録（writer で `R=0` 復元するため）

> 備考：`surface_cmds` へ `STO` を入れてもよいが、STOP の正は `SurfaceSpec.stop` とし、writer が stop 面に `STO` を出力する。

---

## 2. `seq_convert.py` の仕様

### 2.1 目的
- `.seq` テキスト/ファイルを解析して `SeqDocument` を生成する
- `SeqDocument` を `.seq` テキスト/ファイルへ書き戻す（正規化）
- `SeqDocument` から `ReportConfig` を構築する（ABCDレポート用規約を適用）
- 描画/解析で必要な `field_angles_deg` と `fno` の決定を補助する

### 2.2 パース仕様（.seq → SeqDocument）

#### (A) 行継続 `&`
- 行末が `&` の場合、次行を連結して 1 行として扱う（`microscope.seq` 対応）
- 連結後の余分な空白は正規化してよい

#### (B) 複合コマンド `;`
- `CCY 0 ; THC 0` のような行は `;` で分割し、各セグメントを独立コマンドとして解釈できること
- ただし `raw_cmds` への保存は「原文行のまま」または「分割後に個別保存」いずれでも良い（仕様上は後者推奨）

#### (C) 面行（SO / S / SI）
以下の行頭トークンを面行とする：

- `SO`（object surface）
- `S`（通常面）
- `SI`（image surface）

面行フォーマット（サブセット）：
```
SO R t [glass]
S  R t [glass]
SI R t [glass]
```

対応：
- `SurfaceSpec.num` は面行の出現順に `1..N`
- `R==0` は内部表現で `R=10000000.0` とし、同時に `conditions.plane_surfaces` に面番号を追加
- `glass` 省略時は `"air"`

#### (D) STOP（STO）
- `STO` は直前面に適用される
- パース結果：該当 `SurfaceSpec.stop=True`

#### (E) 条件行（Lens条件）
以下は `SeqConditions` の対応フィールドにパースする：

- `TITLE ...` → `title`
- `DIM M` → `dim="M"`
- `WL ...` → `wavelengths`
- `XAN ...` → `xan_deg`
- `YAN ...` → `yan_deg`
- `EPD ...` → `epd`
- `FNO ...` → `fno`
- `NA ...` → `na`
- `NAO ...` → `nao`（opticspy の簡易パーサが `NA` のみ対応でも保持する）

#### (F) 面に紐づかない行（raw_cmds）
上記に該当しない行は **原則として** `raw_cmds` に保存する。

例：`INI`, `WTW`, `WTF`, `VUX/VUY/VLX/VLY`, `CA`, `PIM`, `GO`, `RDM`, `LEN`, `DER ...`, `REF ...` など

#### (G) 面直後の補助行（surface_cmds）
面行（SO/S/SI）直後に現れることが多いコマンドを、直前の面番号に紐付けて保持する。

例：`CCY`, `THC`, `CIR`, `CIR EDG`, `EDG`, `CUY ...`

---

### 2.3 書き戻し仕様（SeqDocument → .seq）

- 出力は正規化され、元ファイルと行単位で完全一致する必要はない
- 保証する意味的同値：
  - 面列（R, t, glass, stop）が同一
  - 主要条件（WL/XAN/YAN/EPD/FNO/NA/NAO/DIM/TITLE 等）が保持
  - `raw_cmds` / `surface_cmds` が保持され再出力される
  - `plane_surfaces` を参照し `R=0` を復元できる

推奨出力順：
1. `TITLE`（あれば）
2. `DIM`（あれば）
3. `WL`, `EPD`, `XAN`, `YAN`, `FNO`, `NA`, `NAO`（存在するもの）
4. 面列：`SO`（1面目）→ `S`（中間）→ `SI`（最終）
5. 各面の直後に `surface_cmds[num]`
6. stop 面（`SurfaceSpec.stop`）の直後に `STO`
7. `raw_cmds`（位置復元をしない場合は末尾へまとめる）

> 位置復元が必要になった場合は、`raw_cmds` に位置情報を持たせる拡張を行う。

---

### 2.4 `ReportConfig` 構築規約（SeqDocument → ReportConfig）
`.seq` の慣習として

- 面1：`SO`（object）
- 最終面：`SI`（image）

を仮定し、ABCD計算用の規約を適用する。

- `reference_surface = 2`
- `start_surface = 2`
- `image_surface = N`
- `end_surface = N-1`
- `wavelengths_nm = conditions.wavelengths`（単位は運用で統一：nm/µm）

---

### 2.5 描画補助
- `pick_field_angles_deg(conditions)`  
  優先：`YAN` → `XAN` → `[0.0]`
- `pick_fno(conditions, fallback_fno)`  
  `conditions.fno` があれば採用、無ければ `fallback_fno`

---

## 3. `yaml_io.py` の仕様

### 3.1 目的
`SurfaceSpec`, `ReportConfig`, `SeqConditions`, `SeqDocument` を YAML に安全に保存・復元する。

- 使用 API：`yaml.safe_dump`, `yaml.safe_load`
- 変換方式：dataclass/クラスを dict/list へ変換して dump、load 時に復元

### 3.2 提供 API（例）
- `dump_surface_specs(path, specs)` / `load_surface_specs(path) -> List[SurfaceSpec]`
- `dump_report_config(path, cfg)` / `load_report_config(path) -> ReportConfig`
- `dump_seq_conditions(path, cond)` / `load_seq_conditions(path) -> SeqConditions`
- `dump_seq_document(path, doc)` / `load_seq_document(path) -> SeqDocument`

### 3.3 YAML 目視確認のポイント
- `*.specs.yaml`：面列（R/t/glass/stop）が正しく出ているか
- `*.cond.yaml`：`raw_cmds` に面外コマンドが保存されているか、`surface_cmds` に面直後コマンドが紐付いているか
- `*.cfg.yaml`：`start/end/image/reference` が規約通りか
- `*.doc.yaml`：`prescription` と `conditions` の整合

---

## 4. テスト（round-trip）

### 4.1 `.seq` round-trip
対象：`ex_CodeV/petzval.seq`, `ex_CodeV/microscope.seq`

1. parse → `SeqDocument`
2. writer で `.seq` 生成
3. 再 parse → `SeqDocument`
4. prescription と主要条件が一致することを確認（意味的同値）

### 4.2 YAML round-trip
`SurfaceSpec`, `ReportConfig`, `SeqConditions`, `SeqDocument` を YAML に dump → load し、同値性を確認する。

### 4.3 YAML を残す（目視）
`KEEP_YAML=1` を付けて実行すると `out_yaml/` に YAML を残す（テストスクリプト実装に依存）。

---

以上。
