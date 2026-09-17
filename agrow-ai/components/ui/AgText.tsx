import { Text as RNText, type TextProps as RNTextProps } from 'react-native';

import { useAppTheme } from '@/hooks/useAppTheme';
import { useLanguage } from '@/hooks/useLanguage';
import { cn } from '@/utils/cn';

type Variant =
  | 'headingXL'
  | 'headingL'
  | 'headingM'
  | 'headingS'
  | 'bodyLarge'
  | 'body'
  | 'bodySmall'
  | 'caption'
  | 'label';

type Weight = 'regular' | 'medium' | 'semibold' | 'bold';

type Color =
  | 'default'
  | 'muted'
  | 'disabled'
  | 'primary'
  | 'onPrimary'
  | 'danger'
  | 'success'
  | 'inherit';

export interface AgTextProps extends RNTextProps {
  variant?: Variant;
  weight?: Weight;
  color?: Color;
  center?: boolean;
  className?: string;
}

const variantClass: Record<Variant, string> = {
  headingXL: 'text-[32px] leading-[40px]',
  headingL: 'text-[28px] leading-[36px]',
  headingM: 'text-[24px] leading-[32px]',
  headingS: 'text-[20px] leading-[28px]',
  bodyLarge: 'text-[18px] leading-[27px]',
  body: 'text-[16px] leading-[24px]',
  bodySmall: 'text-[14px] leading-[21px]',
  caption: 'text-[12px] leading-[18px]',
  label: 'text-[14px] leading-[20px]',
};

const interWeight: Record<Weight, string> = {
  regular: 'font-sans',
  medium: 'font-medium',
  semibold: 'font-semibold',
  bold: 'font-bold',
};

const tamilWeight: Record<Weight, string> = {
  regular: 'font-tamil',
  medium: 'font-tamil-medium',
  semibold: 'font-tamil-semibold',
  bold: 'font-tamil-bold',
};

const colorClass: Record<Color, string> = {
  default: 'text-content',
  muted: 'text-content-muted',
  disabled: 'text-content-disabled',
  primary: 'text-primary',
  onPrimary: 'text-on-primary',
  danger: 'text-danger',
  success: 'text-success',
  inherit: '',
};

/**
 * Typography primitive. Encapsulates the type scale, theme colors, and — key for
 * a Tamil-first app — automatic font-family switching (Noto Sans Tamil in Tamil,
 * Inter in English). Screens never hardcode font/size/color.
 */
export function AgText({
  variant = 'body',
  weight = 'regular',
  color = 'default',
  center,
  className,
  maxFontSizeMultiplier = 1.6,
  ...rest
}: AgTextProps) {
  const { isTamil } = useLanguage();
  const { colors, isSunlight } = useAppTheme();
  const weightClass = (isTamil ? tamilWeight : interWeight)[weight];
  const scale = isSunlight ? 1.18 : 1;
  const baseVariant = {
    headingXL: { fontSize: 32, lineHeight: 40 },
    headingL: { fontSize: 28, lineHeight: 36 },
    headingM: { fontSize: 24, lineHeight: 32 },
    headingS: { fontSize: 20, lineHeight: 28 },
    bodyLarge: { fontSize: 18, lineHeight: 27 },
    body: { fontSize: 16, lineHeight: 24 },
    bodySmall: { fontSize: 14, lineHeight: 21 },
    caption: { fontSize: 12, lineHeight: 18 },
    label: { fontSize: 14, lineHeight: 20 },
  }[variant];
  const nativeVariant = {
    fontSize: Math.round(baseVariant.fontSize * scale),
    lineHeight: Math.round(baseVariant.lineHeight * scale),
  };
  const nativeColor = {
    default: colors.text,
    muted: colors.textMuted,
    disabled: colors.textDisabled,
    primary: colors.primary,
    onPrimary: colors.onPrimary,
    danger: colors.danger,
    success: colors.success,
    inherit: undefined,
  }[color];

  return (
    <RNText
      // Respect OS font scaling for accessibility, but cap extreme sizes.
      {...rest}
      maxFontSizeMultiplier={maxFontSizeMultiplier}
      style={[
        nativeVariant,
        { color: nativeColor, textAlign: center ? 'center' : undefined },
        rest.style,
      ]}
      className={cn(
        variantClass[variant],
        weightClass,
        colorClass[color],
        center && 'text-center',
        className,
      )}
    />
  );
}
