# SF UI コンポーネントガイド

## コンポーネント一覧と使用例

### SciFiPanel

角を斜めにカットした枠線と走査線エフェクトを持つコンテナコンポーネント。

#### Props
```typescript
interface SciFiPanelProps {
  children: ReactNode;
  className?: string;
  variant?: "primary" | "secondary" | "accent";  // デフォルト: "primary"
  scanline?: boolean;  // デフォルト: true
  chiseled?: boolean;  // デフォルト: true
}
```

#### 使用例
```tsx
// Primary (Neon Green) - 標準、肯定的な内容
<SciFiPanel variant="primary">
  <div className="p-6">Content</div>
</SciFiPanel>

// Secondary (Amber) - 警告、重要な情報
<SciFiPanel variant="secondary">
  <div className="p-6">Warning Content</div>
</SciFiPanel>

// Accent (Cyan) - 情報、技術的な詳細
<SciFiPanel variant="accent">
  <div className="p-6">Technical Info</div>
</SciFiPanel>

// 走査線なし、角の切り込みなしバージョン
<SciFiPanel variant="primary" scanline={false} chiseled={false}>
  <div className="p-6">Simple Panel</div>
</SciFiPanel>
```

---

### SciFiButton

ホバー時にグロー効果が出るSF風ボタン。

#### Props
```typescript
interface SciFiButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  children: ReactNode;
  variant?: "primary" | "secondary" | "accent" | "danger";
  size?: "sm" | "md" | "lg";
}
```

#### 使用例
```tsx
// Primary - 主要なアクション
<SciFiButton variant="primary" size="md">
  Execute
</SciFiButton>

// Secondary - 警告を伴うアクション
<SciFiButton variant="secondary" size="lg">
  Purchase
</SciFiButton>

// Accent - 情報的なアクション
<SciFiButton variant="accent" size="sm">
  Details
</SciFiButton>

// Danger - 危険な操作
<SciFiButton variant="danger" onClick={handleDelete}>
  Delete
</SciFiButton>

// Disabled状態
<SciFiButton variant="primary" disabled>
  Processing...
</SciFiButton>
```

---

### SciFiHeading

ターミナル風の見出し装飾を持つヘッダーコンポーネント。

#### Props
```typescript
interface SciFiHeadingProps {
  children: ReactNode;
  level?: 1 | 2 | 3 | 4;  // デフォルト: 1
  className?: string;
  variant?: "primary" | "secondary" | "accent";
}
```

#### 使用例
```tsx
// h1 タグ、Primary色
<SciFiHeading level={1} variant="primary">
  MAIN TITLE
</SciFiHeading>

// h2 タグ、Secondary色
<SciFiHeading level={2} variant="secondary">
  Section Title
</SciFiHeading>

// h3 タグ、Accent色
<SciFiHeading level={3} variant="accent">
  Subsection
</SciFiHeading>

// h4 タグ
<SciFiHeading level={4}>
  Detail Heading
</SciFiHeading>
```

---

### SciFiInput

SF風の入力フォーム。ラベルとヘルプテキストをサポート。

#### Props
```typescript
interface SciFiInputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  helpText?: string;
  variant?: "primary" | "secondary" | "accent";
}
```

#### 使用例
```tsx
// 基本的な使用
<SciFiInput
  label="Machine Name"
  type="text"
  value={name}
  onChange={(e) => setName(e.target.value)}
  variant="primary"
/>

// ヘルプテキスト付き
<SciFiInput
  label="Max HP"
  helpText="機体の最大耐久値"
  type="number"
  value={hp}
  onChange={(e) => setHp(Number(e.target.value))}
  variant="accent"
/>

// Secondary色、placeholder付き
<SciFiInput
  label="Credits"
  placeholder="Enter amount"
  type="number"
  variant="secondary"
/>
```

---

### SciFiCard

インタラクティブな情報カード。ホバー時にスケールアニメーション。

#### Props
```typescript
interface SciFiCardProps {
  children: ReactNode;
  className?: string;
  variant?: "primary" | "secondary" | "accent";
  interactive?: boolean;  // デフォルト: false
  onClick?: () => void;
}
```

#### 使用例
```tsx
// インタラクティブなカード
<SciFiCard
  variant="primary"
  interactive
  onClick={() => handleSelect(item)}
>
  <div className="p-4">
    <h3 className="font-bold">{item.name}</h3>
    <p>{item.description}</p>
  </div>
</SciFiCard>

// 静的なカード（クリック不可）
<SciFiCard variant="secondary">
  <div className="p-4">
    <p>Information Display</p>
  </div>
</SciFiCard>

// Accent色、カスタムクラス付き
<SciFiCard 
  variant="accent" 
  interactive 
  className="hover:scale-105"
>
  <div className="p-4">Technical Data</div>
</SciFiCard>
```

---

### SciFiSelect

SF風セレクトボックス。

#### Props
```typescript
interface SciFiSelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  helpText?: string;
  variant?: "primary" | "secondary" | "accent";
  options: { value: string | number; label: string }[];
}
```

#### 使用例
```tsx
// 基本的な使用
<SciFiSelect
  label="Target Priority"
  helpText="攻撃対象の選択方法を設定します"
  variant="accent"
  value={priority}
  onChange={(e) => setPriority(e.target.value)}
  options={[
    { value: "CLOSEST", label: "CLOSEST - 最寄りの敵" },
    { value: "WEAKEST", label: "WEAKEST - HP最小の敵" },
    { value: "STRONGEST", label: "STRONGEST - 強敵優先" },
  ]}
/>

// Secondary色
<SciFiSelect
  label="Difficulty"
  variant="secondary"
  value={difficulty}
  onChange={(e) => setDifficulty(e.target.value)}
  options={[
    { value: "1", label: "Easy" },
    { value: "2", label: "Normal" },
    { value: "3", label: "Hard" },
  ]}
/>
```

---

## カラーパレット使用ガイド

### Primary - Neon Green (#00ff41)
**用途**: 
- デフォルトの要素
- 肯定的な操作 (保存、実行、確認)
- 成功状態の表示
- 自軍・味方の表現
- システム情報

**使用例**:
```tsx
<SciFiButton variant="primary">Save</SciFiButton>
<SciFiPanel variant="primary">Success Message</SciFiPanel>
```

### Secondary - Amber (#ffb000)
**用途**:
- 警告メッセージ
- 重要な情報
- 金銭・クレジット関連
- 実弾兵器
- 敵軍の表現
- 商業的な要素

**使用例**:
```tsx
<SciFiButton variant="secondary">Purchase</SciFiButton>
<SciFiPanel variant="secondary">Warning: Low Credits</SciFiPanel>
```

### Accent - Cyan (#00f0ff)
**用途**:
- 情報的な要素
- 技術的な詳細
- ビーム兵器
- エネルギー関連
- 補助的な操作

**使用例**:
```tsx
<SciFiButton variant="accent">Details</SciFiButton>
<SciFiHeading variant="accent">Technical Specifications</SciFiHeading>
```

### Danger - Red
**用途**:
- 危険な操作 (削除、キャンセル)
- エラーメッセージ
- 失敗状態
- 破壊的なアクション

**使用例**:
```tsx
<SciFiButton variant="danger">Delete</SciFiButton>
```

---

## レイアウトパターン

### 1. 基本ページレイアウト

```tsx
export default function MyPage() {
  return (
    <main className="min-h-screen bg-[#050505] text-[#00ff41] p-8 font-mono">
      <div className="max-w-4xl mx-auto">
        <Header />
        
        <SciFiPanel variant="primary">
          <div className="p-6">
            <SciFiHeading level={1}>Page Title</SciFiHeading>
            {/* Content */}
          </div>
        </SciFiPanel>
      </div>
    </main>
  );
}
```

### 2. 2カラムレイアウト

```tsx
<div className="grid grid-cols-1 md:grid-cols-2 gap-6">
  {/* Left Column */}
  <SciFiPanel variant="primary">
    <div className="p-6">
      <SciFiHeading level={3}>Left Panel</SciFiHeading>
      {/* Content */}
    </div>
  </SciFiPanel>
  
  {/* Right Column */}
  <SciFiPanel variant="accent">
    <div className="p-6">
      <SciFiHeading level={3} variant="accent">Right Panel</SciFiHeading>
      {/* Content */}
    </div>
  </SciFiPanel>
</div>
```

### 3. カードグリッドレイアウト

```tsx
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
  {items.map((item) => (
    <SciFiCard
      key={item.id}
      variant="secondary"
      interactive
      onClick={() => handleSelect(item)}
    >
      <div className="p-4">
        <h3 className="font-bold text-[#ffb000]">{item.name}</h3>
        <p className="text-sm text-[#00ff41]/60">{item.description}</p>
      </div>
    </SciFiCard>
  ))}
</div>
```

### 4. フォームレイアウト

```tsx
<SciFiPanel variant="accent">
  <div className="p-6">
    <SciFiHeading level={2} variant="accent">Form Title</SciFiHeading>
    
    <form onSubmit={handleSubmit} className="space-y-4 mt-4">
      <SciFiInput
        label="Field 1"
        type="text"
        variant="accent"
        value={field1}
        onChange={(e) => setField1(e.target.value)}
      />
      
      <SciFiSelect
        label="Field 2"
        variant="accent"
        value={field2}
        onChange={(e) => setField2(e.target.value)}
        options={options}
      />
      
      <SciFiButton type="submit" variant="accent" size="lg" className="w-full">
        Submit
      </SciFiButton>
    </form>
  </div>
</SciFiPanel>
```

---

## スタイリングのベストプラクティス

### 1. 色の透明度

SF感を出すために透明度を活用:
```tsx
className="text-[#00ff41]/60"  // 60% opacity
className="bg-[#0a0a0a]/80"    // 80% opacity  
className="border-[#ffb000]/30" // 30% opacity
```

### 2. spacing の一貫性

```tsx
// Padding: p-4 (小), p-6 (中), p-8 (大)
// Gap: gap-4 (小), gap-6 (中), gap-8 (大)
// Margin: mb-4 (小), mb-6 (中), mb-8 (大)
```

### 3. フォントサイズ

```tsx
// 見出し: text-3xl, text-2xl, text-xl
// 本文: text-base
// 小文字: text-sm
// 極小: text-xs
```

### 4. レスポンシブデザイン

```tsx
className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3"
className="text-xl md:text-2xl"
className="p-4 md:p-6"
```

---

## アニメーションクラス

### 既存のアニメーション
```tsx
// パルス (点滅)
className="animate-pulse"

// トランジション
className="transition-all duration-200"
className="transition-colors"

// ホバー効果
className="hover:scale-[1.02]"
className="hover:border-[#00ff41]"
```

---

## トラブルシューティング

### Q: グロー効果が表示されない
A: `sf-border-glow-*` クラスが適用されているか確認してください。また、border-colorが設定されている必要があります。

### Q: 走査線が見えない
A: `sf-scanline` クラスと `position: relative` が必要です。SciFiPanelを使用する場合は自動的に適用されます。

### Q: カスタム色を使いたい
A: Tailwindのarbitrary valuesを使用:
```tsx
className="bg-[#custom-color] text-[#another-color]"
```

### Q: フォントが等幅にならない
A: `font-mono` クラスを追加してください:
```tsx
className="font-mono"
```

---

## まとめ

このUIコンポーネントキットにより:
- ✅ 一貫性のあるデザイン
- ✅ 高い再利用性
- ✅ 型安全性
- ✅ カスタマイズ性

を実現しています。新しいページや機能を追加する際は、このガイドを参照して統一されたUIを構築してください。
