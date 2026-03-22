import { useCallback, useContext, useEffect } from "react";
import { UNSAFE_NavigationContext, useBeforeUnload } from "react-router-dom";

interface Transition {
  retry: () => void;
}

interface NavigatorWithBlock {
  block?: (listener: (transition: Transition) => void) => () => void;
}

export function useUnsavedChangesWarning(when: boolean, message: string) {
  const navigationContext = useContext(UNSAFE_NavigationContext) as {
    navigator: NavigatorWithBlock;
  };

  useBeforeUnload(
    (event) => {
      if (!when) return;
      event.preventDefault();
      event.returnValue = message;
    },
    { capture: true },
  );

  const blocker = useCallback(
    (transition: Transition) => {
      const shouldLeave = window.confirm(message);
      if (shouldLeave) {
        transition.retry();
      }
    },
    [message],
  );

  useEffect(() => {
    if (!when || typeof navigationContext.navigator.block !== "function") {
      return undefined;
    }

    const unblock = navigationContext.navigator.block((transition) => {
      blocker({
        ...transition,
        retry() {
          unblock();
          transition.retry();
        },
      });
    });

    return unblock;
  }, [blocker, navigationContext.navigator, when]);
}
