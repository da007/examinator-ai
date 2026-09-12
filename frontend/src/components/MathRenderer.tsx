import { useMemo } from 'react';
import katex from 'katex';
import 'katex/dist/katex.min.css';
import DOMPurify from 'dompurify';
import { clsx } from 'clsx';

interface MathRendererProps {
  formula: string;
  displayMode?: boolean;
  className?: string;
}

export function MathRenderer({ formula, displayMode = false, className }: MathRendererProps) {
  const html = useMemo(() => {
    try {
      const rendered = katex.renderToString(formula, {
        displayMode,
        throwOnError: false,
        strict: false,
      });
      return DOMPurify.sanitize(rendered);
    } catch (error) {
      console.error('KaTeX rendering error:', error);
      return DOMPurify.sanitize(formula);
    }
  }, [formula, displayMode]);

  return (
    <span
      className={clsx("math-renderer select-all", className)}
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}