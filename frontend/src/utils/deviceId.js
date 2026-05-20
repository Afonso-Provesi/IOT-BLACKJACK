const KEY = 'bj_device_id'

/**
 * Returns a stable UUID for this browser. Generated once and stored in
 * localStorage so it survives page reloads but is unique per device/browser.
 */
export function getDeviceId() {
  let id = localStorage.getItem(KEY)
  if (!id) {
    id = crypto.randomUUID()
    localStorage.setItem(KEY, id)
  }
  return id
}
