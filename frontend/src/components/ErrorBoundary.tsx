import React, { Component, ErrorInfo, ReactNode } from 'react';
import { AlertCircle, RefreshCcw, Home } from 'lucide-react';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Uncaught error:', error, errorInfo);
  }

  private handleReset = () => {
    window.location.reload();
  };

  private handleGoHome = () => {
    window.location.href = '/';
  };

  public render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-app flex items-center justify-center p-6 text-center">
          <div className="max-w-md w-full animate-in fade-in zoom-in-95 duration-500">
            <div className="w-20 h-20 bg-destructive/10 text-destructive rounded-[2rem] flex items-center justify-center mx-auto mb-8 shadow-lg shadow-destructive/5">
              <AlertCircle size={40} />
            </div>
            
            <h1 className="text-2xl font-black text-app mb-4 tracking-tight">Произошла ошибка</h1>
            <p className="text-sm text-muted-app mb-10 leading-relaxed">
              Что-то пошло не так при отрисовке интерфейса. Попробуйте обновить страницу или вернуться на главную.
            </p>

            <div className="flex flex-col sm:flex-row gap-3 justify-center">
              <button
                onClick={this.handleReset}
                className="flex items-center justify-center gap-2 px-6 py-3 bg-primary text-white rounded-xl font-bold text-sm hover:bg-primary-hover transition-all shadow-lg shadow-primary/20"
              >
                <RefreshCcw size={18} /> ОБНОВИТЬ
              </button>
              <button
                onClick={this.handleGoHome}
                className="flex items-center justify-center gap-2 px-6 py-3 bg-app border border-app text-app rounded-xl font-bold text-sm hover:bg-surface-alt transition-all"
              >
                <Home size={18} /> НА ГЛАВНУЮ
              </button>
            </div>

            {import.meta.env.DEV && this.state.error && (
              <div className="mt-12 p-4 bg-black/5 rounded-lg text-left overflow-auto max-h-40">
                <p className="text-[10px] font-mono text-destructive uppercase font-bold mb-2">Debug Info:</p>
                <code className="text-[10px] font-mono opacity-70">{this.state.error.toString()}</code>
              </div>
            )}
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}