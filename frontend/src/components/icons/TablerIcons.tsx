/* frontend/src/components/icons/TablerIcons.tsx */

/*
 * Tabler Icons (outline, https://tabler.io/icons, MIT License) のパスをローカルに複製したもの。
 * frontend/CLAUDE.md の方針(アイコンライブラリ非導入)に従い、依存追加ではなくSVGパスの
 * インライン実装で統一する。アバター・ボトムナビ等、UI全体で同一セットのみを使用すること。
 */

export type TablerIconProps = {
  className?: string;
};

const baseProps = {
  xmlns: "http://www.w3.org/2000/svg",
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 2,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
  "aria-hidden": true,
};

export function IconHome({ className }: TablerIconProps) {
  return (
    <svg {...baseProps} className={className}>
      <path stroke="none" d="M0 0h24v24H0z" fill="none" />
      <path d="M5 12l-2 0l9 -9l9 9l-2 0" />
      <path d="M5 12v7a2 2 0 0 0 2 2h10a2 2 0 0 0 2 -2v-7" />
      <path d="M9 21v-6a2 2 0 0 1 2 -2h2a2 2 0 0 1 2 2v6" />
    </svg>
  );
}

export function IconTool({ className }: TablerIconProps) {
  return (
    <svg {...baseProps} className={className}>
      <path stroke="none" d="M0 0h24v24H0z" fill="none" />
      <path d="M7 10h3v-3l-3.5 -3.5a6 6 0 0 1 8 8l6 6a2 2 0 0 1 -3 3l-6 -6a6 6 0 0 1 -8 -8l3.5 3.5" />
    </svg>
  );
}

export function IconShoppingCart({ className }: TablerIconProps) {
  return (
    <svg {...baseProps} className={className}>
      <path stroke="none" d="M0 0h24v24H0z" fill="none" />
      <path d="M6 19a1 1 0 1 0 2 0a1 1 0 1 0 -2 0" />
      <path d="M17 19a1 1 0 1 0 2 0a1 1 0 1 0 -2 0" />
      <path d="M17 17h-11v-14h-2" />
      <path d="M6 5l14 1l-1 7h-13" />
    </svg>
  );
}

export function IconHistory({ className }: TablerIconProps) {
  return (
    <svg {...baseProps} className={className}>
      <path stroke="none" d="M0 0h24v24H0z" fill="none" />
      <path d="M12 8l0 4l2 2" />
      <path d="M3.05 11a9 9 0 1 1 .5 4m-.5 5v-5h5" />
    </svg>
  );
}

export function IconUsers({ className }: TablerIconProps) {
  return (
    <svg {...baseProps} className={className}>
      <path stroke="none" d="M0 0h24v24H0z" fill="none" />
      <path d="M9 7m-4 0a4 4 0 1 0 8 0a4 4 0 1 0 -8 0" />
      <path d="M3 21v-2a4 4 0 0 1 4 -4h4a4 4 0 0 1 4 4v2" />
      <path d="M16 3.13a4 4 0 0 1 0 7.75" />
      <path d="M21 21v-2a4 4 0 0 0 -3 -3.85" />
    </svg>
  );
}

export function IconUser({ className }: TablerIconProps) {
  return (
    <svg {...baseProps} className={className}>
      <path stroke="none" d="M0 0h24v24H0z" fill="none" />
      <path d="M8 7a4 4 0 1 0 8 0a4 4 0 0 0 -8 0" />
      <path d="M6 21v-2a4 4 0 0 1 4 -4h4a4 4 0 0 1 4 4v2" />
    </svg>
  );
}

export function IconMenu2({ className }: TablerIconProps) {
  return (
    <svg {...baseProps} className={className}>
      <path stroke="none" d="M0 0h24v24H0z" fill="none" />
      <path d="M4 6l16 0" />
      <path d="M4 12l16 0" />
      <path d="M4 18l16 0" />
    </svg>
  );
}
