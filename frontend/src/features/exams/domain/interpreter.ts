import { 
  ArrowRight, 
  CheckCircle, 
  Info, 
  Edit3,
  type LucideIcon 
} from 'lucide-react';

export type InterpretedInput =
  | { kind: 'command'; command: string; arg: string }
  | { kind: 'answer'; text: string };

export function interpretInput(raw: string): InterpretedInput {
  const trimmed = raw.trim();
  if (trimmed.startsWith('/')) {
    const spaceIdx = trimmed.indexOf(' ');
    const command = spaceIdx === -1 ? trimmed : trimmed.slice(0, spaceIdx);
    const arg = spaceIdx === -1 ? '' : trimmed.slice(spaceIdx + 1).trim();
    return { kind: 'command', command: command.toLowerCase(), arg };
  }
  return { kind: 'answer', text: trimmed };
}

// ── Command Protocol ──────────────────────────────────────────────────────────

export interface CommandContext {
  isLastQuestion: boolean;
  canEdit: boolean;
  actions: {
    goToNext: () => void;
    submit: () => void;
    editQuestion: (id: string) => void;
    showStatus: () => void;
  };
}

export interface CommandDefinition {
  command: string;
  label: string;
  icon: LucideIcon;
  isVisible: (ctx: CommandContext) => boolean;
  handler: (arg: string, ctx: CommandContext) => void;
}

export const COMMANDS: CommandDefinition[] = [
  {
    command: '/next',
    label: 'Пропустить',
    icon: ArrowRight,
    isVisible: (ctx) => !ctx.isLastQuestion,
    handler: (_, ctx) => ctx.actions.goToNext(),
  },
  {
    command: '/submit',
    label: 'Сдать экзамен',
    icon: CheckCircle,
    isVisible: () => true,
    handler: (_, ctx) => ctx.actions.submit(),
  },
  {
    command: '/edit',
    label: 'Исправить №',
    icon: Edit3,
    isVisible: () => true, // Теперь всегда доступно в чате
    handler: (arg, ctx) => {
      if (!arg) return;
      ctx.actions.editQuestion(arg);
    },
  },
  {
    command: '/status',
    label: 'Инфо',
    icon: Info,
    isVisible: () => true,
    handler: (_, ctx) => ctx.actions.showStatus(),
  },
];

export function executeCommand(
  interpreted: Extract<InterpretedInput, { kind: 'command' }>,
  ctx: CommandContext
): boolean {
  const cmdDef = COMMANDS.find(c => c.command === interpreted.command);
  if (!cmdDef) return false;
  cmdDef.handler(interpreted.arg, ctx);
  return true;
}

/** Возвращает список команд, для которых нужно отрисовать кнопки-чипсы */
export function getVisibleCommands(ctx: CommandContext): CommandDefinition[] {
  return COMMANDS.filter(c => c.isVisible(ctx));
}