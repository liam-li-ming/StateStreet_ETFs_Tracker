interface Props {
  message?: string
}

export function ErrorMessage({ message = 'Something went wrong.' }: Props) {
  return (
    <div className="rounded-lg border border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-900/20 p-4 text-red-700 dark:text-red-400">
      {message}
    </div>
  )
}
