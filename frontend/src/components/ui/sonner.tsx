import { useTheme } from "next-themes"
import type { CSSProperties } from "react"
import { Toaster as Sonner } from "sonner"

type ToasterProps = React.ComponentProps<typeof Sonner>

const Toaster = ({ ...props }: ToasterProps) => {
  const { theme = "light" } = useTheme()

  return (
    <Sonner
      theme={theme as ToasterProps["theme"]}
      className="toaster group"
      richColors
      closeButton
      style={{
        "--error-bg": "#fff1f2",
        "--error-border": "#fecdd3",
        "--error-text": "#9f1239",
      } as CSSProperties}
      toastOptions={{
        classNames: {
          toast:
            "group toast shadow-lg",
          actionButton:
            "group-[.toast]:bg-primary group-[.toast]:text-primary-foreground",
          cancelButton:
            "group-[.toast]:bg-muted group-[.toast]:text-muted-foreground",
        },
      }}
      {...props}
    />
  )
}

export { Toaster }
