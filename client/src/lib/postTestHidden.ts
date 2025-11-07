export const POST_TEST_HIDDEN_KEY = 'postTestHidden';

export function getPostTestHidden(): boolean {
  try {
    return localStorage.getItem(POST_TEST_HIDDEN_KEY) === 'true';
  } catch (e) {
    return false;
  }
}

export function setPostTestHidden(val: boolean = true) {
  try {
    localStorage.setItem(POST_TEST_HIDDEN_KEY, val ? 'true' : 'false');
  } catch (e) {
    // ignore
  }
}
