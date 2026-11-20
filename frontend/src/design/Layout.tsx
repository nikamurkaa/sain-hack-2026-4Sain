import { useLayoutEffect, useRef, useState } from "react";
import type { CSSProperties, ReactNode } from "react";
import frames from "./frames.json";
import backgrounds from "./backgrounds.json";
import "./layout.css";

type Label = {
  value: string;
  lines?: string;
  box: number[];
  font: string;
  size: number;
  weight: number;
  line: number;
  tracking: number;
  align: string;
  color: string;
};
type Indicator = {
  kind: string;
  box: number[];
  thumb: number[];
  ratio: number;
};
export type Widget = {
  name: string;
  box: number[];
  texts: Label[];
  art?: string;
  controls?: Indicator[];
};
export type Binding = {
  text?: (value: string, index: number) => string;
  level?: number | null;
  onClick?: () => void;
  label?: string;
  title?: string;
  disabled?: boolean;
  className?: string;
  role?: string;
  hidden?: boolean;
  content?: ReactNode;
  children?: ReactNode;
};
export const layouts: { title: string; blocks: Widget[] }[] = frames;
const drawings = import.meta.glob<string>("./art-*.svg", {
  eager: true,
  import: "default",
  query: "?raw",
});
export function Shapes({ screen }: { screen: number }) {
  // Static, text-free Figma paths compiled into the application at build time.
  const svg = drawings["./art-" + String(screen).padStart(2, "0") + ".svg"];
  return (
    <div
      className="design-defs"
      aria-hidden
      dangerouslySetInnerHTML={{ __html: svg }}
    />
  );
}
export function rect([left, top, width, height]: number[]): CSSProperties {
  return { position: "absolute", left, top, width, height };
}
function IndicatorView({
  control,
  level,
}: {
  control: Indicator;
  level?: number | null;
}) {
  if (level === null) return null;
  const ratio = Math.max(0, Math.min(1, level ?? control.ratio));
  const isSwitch = control.kind === "switch",
    thumb = control.thumb;
  const left = isSwitch
    ? ratio > 0.5
      ? control.box[2] - thumb[2] - 2
      : 2
    : ratio * (control.box[2] - thumb[2]);
  return (
    <span
      aria-hidden
      className={
        "design-indicator indicator-" +
        control.kind +
        (ratio > 0.5 ? " on" : "")
      }
      style={rect(control.box)}
    >
      {!isSwitch && <i style={{ width: left + thumb[2] / 2 }} />}
      <b style={rect([left, thumb[1], thumb[2], thumb[3]])} />
    </span>
  );
}
export function DesignWidget({
  screen,
  widget,
  bind = {},
}: {
  screen: number;
  widget: Widget;
  bind?: Binding;
}) {
  if (bind.hidden) return null;
  const Tag = bind.onClick ? "button" : "div";
  const [, , width, height] = widget.box;
  return (
    <Tag
      type={Tag === "button" ? "button" : undefined}
      aria-label={bind.label}
      title={bind.title}
      disabled={bind.disabled}
      role={bind.role}
      onClick={bind.onClick}
      className={"design-widget " + (bind.className ?? "")}
      style={rect(widget.box)}
    >
      {widget.art && (
        <svg
          aria-hidden="true"
          fill="none"
          className="widget-art"
          width={width}
          height={height}
          viewBox={`0 0 ${width} ${height}`}
        >
          <use href={`#s${screen}-${widget.art}`} />
        </svg>
      )}
      {widget.controls?.map((c, i) => (
        <IndicatorView key={i} control={c} level={bind.level} />
      ))}
      {bind.content !== undefined
        ? bind.content
        : widget.texts.map((t, i) => {
            const value = bind.text ? bind.text(t.value, i) : t.value;
            const style: CSSProperties = {
              ...rect(t.box),
              fontFamily: t.font + ", sans-serif",
              fontSize: t.size,
              fontWeight: t.weight,
              lineHeight: t.line + "px",
              letterSpacing: t.tracking,
              textAlign: t.align as CSSProperties["textAlign"],
              color: t.color,
            };
            const original = value === t.value;
            if (!original && (widget.texts.length === 1 || width >= 150)) {
              style.width = Math.max(
                t.box[2],
                width - t.box[0] - (width >= 150 ? 12 : 0),
              );
              if (t.font === "Inter") style.width = 55;
            }
            return (
              <span
                className={"design-label" + (original ? " original" : "")}
                key={i}
                style={style}
              >
                {((original ? t.lines : undefined) ?? value).replaceAll(
                  "\u2028",
                  "\n",
                )}
              </span>
            );
          })}
      {bind.children}
    </Tag>
  );
}
export function DesignScreen({
  screen,
  bind,
  children,
}: {
  screen: number;
  bind?: (widget: Widget, index: number) => Binding | undefined;
  children?: ReactNode;
}) {
  const wrapper = useRef<HTMLDivElement>(null);
  const [scale, setScale] = useState(1);
  useLayoutEffect(() => {
    const el = wrapper.current!;
    const update = () => setScale(el.clientWidth / 375);
    update();
    const observer = new ResizeObserver(update);
    observer.observe(el);
    return () => observer.disconnect();
  }, []);
  return (
    <div ref={wrapper} className="design-shell">
      <Shapes screen={screen} />
      <div style={{ height: 812 * scale }}>
        <main
          className="design-frame"
          style={{ transform: `scale(${scale})` }}
          data-frame={screen}
        >
          <svg aria-hidden className="frame-paint" width="375" height="812">
            <rect
              width="375"
              height="812"
              fill={`url(#${backgrounds[screen - 1]})`}
            />
          </svg>
          {layouts[screen - 1].blocks.map((widget, i) => (
            <DesignWidget
              key={screen + "-" + i}
              screen={screen}
              widget={widget}
              bind={bind?.(widget, i)}
            />
          ))}
          {children}
        </main>
      </div>
    </div>
  );
}

// Desktop columns reuse the same widgets at their column's width.
export function ResponsiveWidget({
  screen,
  widget,
  bind,
}: {
  screen: number;
  widget: Widget;
  bind?: Binding;
}) {
  const root = useRef<HTMLDivElement>(null),
    [scale, set] = useState(1);
  useLayoutEffect(() => {
    const el = root.current!,
      resize = () => set(el.clientWidth / widget.box[2]);
    resize();
    const observer = new ResizeObserver(resize);
    observer.observe(el);
    return () => observer.disconnect();
  }, [widget.box]);
  return (
    <div
      ref={root}
      className="responsive-widget"
      style={{ aspectRatio: widget.box[2] + "/" + widget.box[3] }}
    >
      <div
        style={{
          position: "relative",
          transformOrigin: "top left",
          transform: `scale(${scale})`,
        }}
      >
        <DesignWidget
          screen={screen}
          widget={{ ...widget, box: [0, 0, ...widget.box.slice(2)] }}
          bind={bind}
        />
      </div>
    </div>
  );
}
