import { type TextStyle, View } from 'react-native';

import { cn } from '@/utils/cn';

import { AgText } from './AgText';

type Tone = 'primary' | 'success' | 'warning' | 'danger' | 'info' | 'neutral';

interface AgBadgeProps {
  label: string;
  tone?: Tone;
  className?: string;
  textStyle?: TextStyle;
  light?: boolean;
}

const toneClass: Record<Tone, { bg: string; text: string }> = {
  primary: { bg: 'bg-primary/12', text: 'text-primary' },
  success: { bg: 'bg-success/15', text: 'text-success' },
  warning: { bg: 'bg-warning/15', text: 'text-warning' },
  danger: { bg: 'bg-danger/12', text: 'text-danger' },
  info: { bg: 'bg-info/12', text: 'text-info' },
  neutral: { bg: 'bg-border/60', text: 'text-content-muted' },
};

const lightTone: Record<Tone, { bg: string; text: string }> = {
  primary: { bg: '#E5F0E1', text: '#165B33' },
  success: { bg: '#E4F3E8', text: '#176B36' },
  warning: { bg: '#FFF1CC', text: '#805400' },
  danger: { bg: '#FBE7E5', text: '#A32119' },
  info: { bg: '#E3F1F5', text: '#155E75' },
  neutral: { bg: '#ECE9DF', text: '#46534B' },
};

export function AgBadge({ label, tone = 'neutral', className, textStyle, light = false }: AgBadgeProps) {
  const t = toneClass[tone];
  const fixed = lightTone[tone];
  return (
    <View
      className={cn('self-start rounded-full px-2.5 py-1', !light && t.bg, className)}
      style={light ? { backgroundColor: fixed.bg } : undefined}
    >
      <AgText
        variant="caption"
        weight="semibold"
        color={textStyle || light ? 'inherit' : 'default'}
        className={textStyle || light ? undefined : t.text}
        style={[light ? { color: fixed.text } : undefined, textStyle]}
      >
        {label}
      </AgText>
    </View>
  );
}
