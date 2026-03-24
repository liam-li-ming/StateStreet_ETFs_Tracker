interface Props {
  message?: string
}

export function ErrorMessage({ message = 'Something went wrong.' }: Props) {
  return (
    <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-700">
      {message}
    </div>
  )
}
