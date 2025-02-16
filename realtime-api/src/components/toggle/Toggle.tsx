import { useState, useEffect, useRef } from 'react';

export function Toggle({
  defaultValue = false,
  values,
  labels,
  onChange = () => {},
}: {
  defaultValue?: string | boolean;
  values?: string[];
  labels?: string[];
  onChange?: (isEnabled: boolean, value: string) => void;
}) {
  if (typeof defaultValue === 'string') {
    defaultValue = !!Math.max(0, (values || []).indexOf(defaultValue));
  }

  const leftRef = useRef<HTMLDivElement>(null);
  const rightRef = useRef<HTMLDivElement>(null);
  const bgRef = useRef<HTMLDivElement>(null);
  const [value, setValue] = useState<boolean>(defaultValue);

  const toggleValue = () => {
    const v = !value;
    const index = +v;
    setValue(v);
    onChange(v, (values || [])[index]);
  };

  useEffect(() => {
    const leftEl = leftRef.current;
    const rightEl = rightRef.current;
    const bgEl = bgRef.current;
    if (leftEl && rightEl && bgEl) {
      if (value) {
        bgEl.style.left = rightEl.offsetLeft + 'px';
        bgEl.style.width = rightEl.offsetWidth + 'px';
      } else {
        bgEl.style.left = '';
        bgEl.style.width = leftEl.offsetWidth + 'px';
      }
    }
  }, [value]);

  return (
    <div
      className={`
        relative flex items-center gap-2 cursor-pointer overflow-hidden
        bg-bgSecondary text-buttonText h-10 rounded-full
        hover:bg-buttonHover
      `}
      onClick={toggleValue}
    >
      {labels && (
        <div 
          ref={leftRef}
          className={`
            relative px-4 z-[2] select-none transition-colors duration-100 ease-in-out
            ${value ? 'text-[#666]' : 'text-white'}
          `}
        >
          {labels[0]}
        </div>
      )}
      {labels && (
        <div 
          ref={rightRef}
          className={`
            relative px-4 z-[2] select-none transition-colors duration-100 ease-in-out -ml-2
            ${value ? 'text-white' : 'text-[#666]'}
          `}
        >
          {labels[1]}
        </div>
      )}
      <div 
        ref={bgRef}
        className="
          bg-buttonText absolute top-0 left-0 bottom-0 z-[1] rounded-full
          transition-all duration-100 ease-in-out
        "
      />
    </div>
  );
}
