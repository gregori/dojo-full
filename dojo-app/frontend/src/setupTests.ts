import { TextEncoder, TextDecoder } from 'node:util'
import '@testing-library/jest-dom'

// jsdom doesn't provide these globals; react-router-dom needs them.
Object.assign(globalThis, { TextEncoder, TextDecoder })

// React 19 requires this flag to be set explicitly in non-browser test environments,
// otherwise it warns that state updates aren't wrapped in act() even when they are.
;(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true
