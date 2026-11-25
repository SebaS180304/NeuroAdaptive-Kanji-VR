/** A token's value in the current theme (a canvas cannot read CSS variables). */
export function tokenReader(el: HTMLElement) {
  const style = getComputedStyle(el)
  return (name: string) => style.getPropertyValue(name).trim()
}
