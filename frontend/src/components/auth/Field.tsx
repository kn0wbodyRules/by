import * as React from 'react'
import { motion } from 'motion/react'
import { Icon } from '@/components/Icon'
import { cn } from '@/lib/utils'

/**
 * Text field with the two auth-screen interactions from the design brief:
 * a label that floats up on focus/fill, and an underline that draws
 * left-to-right rather than snapping on.
 */
export function Field({
  label,
  type = 'text',
  value,
  onChange,
  autoComplete,
  required,
  placeholder,
}: {
  label: string
  type?: 'text' | 'email' | 'password'
  value: string
  onChange: (v: string) => void
  autoComplete?: string
  required?: boolean
  placeholder?: string
}) {
  const [focused, setFocused] = React.useState(false)
  const [revealed, setRevealed] = React.useState(false)
  const id = React.useId()

  const isPassword = type === 'password'
  const floating = focused || value.length > 0

  return (
    <div className="relative pt-5">
      <motion.label
        htmlFor={id}
        className="font-ui text-navy/70 pointer-events-none absolute left-0 origin-left"
        initial={false}
        animate={{
          y: floating ? 0 : 28,
          scale: floating ? 1 : 1.08,
          opacity: floating ? 1 : 0.55,
        }}
        transition={{ type: 'spring', stiffness: 420, damping: 34 }}
      >
        {label}
      </motion.label>

      <div className="relative mt-1">
        <input
          id={id}
          type={isPassword && revealed ? 'text' : type}
          value={value}
          required={required}
          autoComplete={autoComplete}
          placeholder={floating ? placeholder : ''}
          onChange={(e) => onChange(e.target.value)}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          className={cn(
            'font-body text-navy placeholder:text-navy/30 h-10 w-full bg-transparent',
            'border-navy/20 border-b outline-none',
            isPassword && 'pr-9',
          )}
        />

        {/* The drawn underline sits on top of the resting border. */}
        <motion.span
          className="bg-navy absolute bottom-0 left-0 h-[1.5px] origin-left"
          initial={false}
          animate={{ scaleX: focused ? 1 : 0 }}
          style={{ width: '100%' }}
          transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
        />

        {isPassword && (
          <button
            type="button"
            onClick={() => setRevealed((r) => !r)}
            aria-label={revealed ? 'Hide password' : 'Show password'}
            className="text-navy/50 hover:text-navy absolute right-0 bottom-2 cursor-pointer transition-colors"
          >
            <Icon name={revealed ? 'visibility' : 'visibility_off'} className="text-[18px]" />
          </button>
        )}
      </div>
    </div>
  )
}
