# Claude Code Programming Guide for Langflow

> Comprehensive guide for developing Langflow using Claude Code AI assistant

## Table of Contents

1. [Environment Setup](#environment-setup)
2. [Backend Development](#backend-development)
3. [Frontend Development](#frontend-development)
4. [Testing Guidelines](#testing-guidelines)
5. [Component Creation](#component-creation)
6. [Internationalization (i18n)](#internationalization-i18n)
7. [Documentation Development](#documentation-development)
8. [Code Quality Standards](#code-quality-standards)

---

## Environment Setup

### Prerequisites

**Backend:**
- Python Package Manager: `uv` (>=0.4) for dependency management
- Database: SQLite for development, PostgreSQL for production
- Development Tools: `make` for build coordination

**Frontend:**
- Node.js: v22.12 LTS for JavaScript runtime
- Package Manager: npm (v10.9) for dependency management
- Development Tools: Vite for build tooling

### Starting Services

```bash
# Backend service (port 7860)
make backend

# Frontend service (port 3000)
make frontend

# Full initialization
make init
```

**Health Checks:**
- Backend: http://localhost:7860/health
- Frontend: http://localhost:3000/

---

## Backend Development

### Project Structure

```
src/backend/base/langflow/
├── components/          # Component categories
│   ├── agents/          # Agent components
│   ├── data/           # Data processing
│   ├── embeddings/     # Embedding components
│   ├── input_output/   # I/O components
│   ├── models/         # Language models
│   ├── processing/     # Text processing
│   ├── prompts/        # Prompt components
│   ├── tools/          # Tool components
│   └── vectorstores/   # Vector stores
├── api/                # FastAPI endpoints
│   ├── v1/             # API version 1
│   └── v2/             # API version 2 (future)
└── services/           # Backend services
    └── database/       # Database models
```

### Adding New Components

1. **Create component file** in appropriate subdirectory under `src/backend/base/langflow/components/`

2. **Update `__init__.py`** with alphabetical imports:
   ```python
   from .my_component import MyComponent

   __all__ = [
       "ExistingComponent",
       "MyComponent",  # Add alphabetically
   ]
   ```

3. **Auto-restart:** Backend auto-restarts on save
4. **Refresh browser:** Refresh to see component changes

### Component Development Best Practices

**Component Structure Example:**
```python
from langflow.components.base import Component
from langflow.inputs import DropdownInput, MessageTextInput
from langflow.schema import Message

class MyComponent(Component):
    display_name = "My Component"
    description = "Description of what this component does"
    icon = "component-icon"  # Lucide icon or custom icon
    name = "MyComponent"

    inputs = [
        MessageTextInput(
            name="input_text",
            display_name="Input Text",
            info="Description of this input",
            required=True,
        ),
        DropdownInput(
            name="option",
            display_name="Select Option",
            options=["option1", "option2"],
            value="option1",
        ),
    ]

    outputs = [
        Output(
            name="result",
            display_name="Result",
            method="process_data",
        ),
    ]

    async def process_data(self) -> Message:
        """Main component execution method."""
        # Your logic here
        result = await self.async_operation()
        return Message(
            text=result,
            sender=self.sender,
            session_id=self.session_id,
        )
```

### Async Development Patterns

**Component Async Methods:**
```python
async def run(self) -> MessageType:
    """Main component execution method."""
    result = await self.async_operation()
    return result

async def message_response(self) -> Message:
    """Return a Message object for chat components."""
    return Message(
        text=self.input_value,
        sender=self.sender,
        session_id=self.session_id,
    )
```

**Background Tasks:**
```python
import asyncio

async def process_in_background(self):
    """Process items without blocking."""
    task = asyncio.create_task(self.heavy_operation())

    try:
        result = await task
        return result
    except asyncio.CancelledError:
        await self.cleanup()
        raise
```

**Queue Operations:**
```python
async def queue_processing(self):
    """Non-blocking queue operations."""
    queue = asyncio.Queue()

    # Non-blocking put
    queue.put_nowait(data)

    # Timeout-controlled get
    try:
        result = await asyncio.wait_for(queue.get(), timeout=5.0)
        return result
    except asyncio.TimeoutError:
        raise ComponentError("Processing timeout")
```

### FastAPI Development

**API Structure:**
- API routes: `src/backend/base/langflow/api/`
- Use `client` fixture from `conftest.py` for testing
- Test with `logged_in_headers` for authenticated endpoints

**API Testing Example:**
```python
async def test_flows_endpoint(client, logged_in_headers):
    response = await client.post(
        "api/v1/flows/",
        json=flow_data,
        headers=logged_in_headers
    )
    assert response.status_code == 201
```

### Database Development

**Models Location:** `src/backend/base/langflow/services/database/models/`

**Database Testing:**
- Use in-memory SQLite for tests
- Database tests may fail in batch runs - run individually if needed:
  ```bash
  uv run pytest src/backend/tests/unit/test_database.py
  ```

### Backend Code Quality Workflow

```bash
# 1. Format FIRST (auto-corrects most style issues)
make format_backend

# 2. Run linting
make lint

# 3. Run tests
make unit_tests

# 4. Commit changes
```

**CRITICAL:** Always run `make format_backend` before linting or committing!

---

## Frontend Development

### Directory Structure

```
src/frontend/src/
├── components/          # Reusable UI components
├── pages/              # Page-level components
├── icons/              # Component icons and lazy loading
├── stores/             # State management (Zustand)
├── types/              # TypeScript type definitions
├── utils/              # Utility functions
├── hooks/              # Custom React hooks
├── services/           # API service functions
└── assets/             # Static assets
```

### Key Technologies

- **React 18** with TypeScript
- **Vite** for build tooling and dev server
- **Tailwind CSS** for styling
- **Zustand** for state management
- **React Flow** for flow graph visualization
- **Lucide React** for icons

### State Management with Zustand

**Creating a Store:**
```typescript
// stores/myStore.ts
import { create } from 'zustand';

interface MyState {
  value: string;
  setValue: (value: string) => void;
}

export const useMyStore = create<MyState>((set) => ({
  value: '',
  setValue: (value) => set({ value }),
}));
```

**Using in Components:**
```typescript
// components/MyComponent.tsx
import { useMyStore } from '@/stores/myStore';

export function MyComponent() {
  // ✅ CORRECT: Use single-value selectors
  const value = useMyStore((state) => state.value);
  const setValue = useMyStore((state) => state.setValue);

  return (
    <input
      value={value}
      onChange={(e) => setValue(e.target.value)}
    />
  );
}
```

### ⚠️ CRITICAL: Zustand Selector Best Practices

**NEVER use object literal selectors - they cause infinite render loops!**

This is the **#1 most common bug** in Langflow frontend that has caused production crashes.

#### ❌ WRONG - Unstable Object Selector (Causes Infinite Loop)

```typescript
// DO NOT DO THIS - Creates new object on every render!
const { value, setValue } = useMyStore((state) => ({
  value: state.value,
  setValue: state.setValue,
}));

// Also WRONG - Destructuring without selector
const { value, setValue } = useMyStore();
```

**Why this breaks:**
1. Object literal `{ value, setValue }` creates **new reference** every render
2. Zustand uses `Object.is()` for shallow comparison
3. New reference → Zustand thinks state changed → triggers re-render
4. Component re-renders → creates new object → infinite loop! 💥

**Real-world impact:**
- Application crashes with `Maximum update depth exceeded`
- Error occurs in Radix UI components (Tooltip, Dropdown, etc.)
- Affects entire component tree (parent + all children)
- User sees white screen / error boundary

#### ✅ CORRECT - Stable Single-Value Selectors

```typescript
// Option 1: Separate selectors (RECOMMENDED)
const value = useMyStore((state) => state.value);
const setValue = useMyStore((state) => state.setValue);

// Option 2: Use shallow comparison (if you must use object)
import { shallow } from 'zustand/shallow';
const { value, setValue } = useMyStore(
  (state) => ({ value: state.value, setValue: state.setValue }),
  shallow  // MUST include this!
);
```

**Why this works:**
- Single values have stable references (primitives, stable functions)
- Zustand's shallow comparison works correctly
- Only re-renders when actual values change

#### Real Example from Production Bug Fix (2025-01-13)

**Files affected by this bug:**
- `use-custom-theme.ts` - Caused entire AppHeader to infinite loop
- `langflow-counts.tsx` - Triggered Tooltip infinite re-renders
- `LanguageSwitcher.tsx` - Language switching broken
- `genericIconComponent.tsx` - Icon rendering loops
- `AccountMenu.tsx` - Menu state loops
- Plus 5 more files...

**Symptoms before fix:**
```
Uncaught Error: Maximum update depth exceeded
  at setRef (Radix UI Tooltip)
  at ShadTooltip
  at CustomLangflowCounts
  at AppHeader
  → Infinite loop! Application crashed!
```

**The fix:**
```diff
// Before (BROKEN)
- const { setDark, dark } = useDarkStore((state) => ({
-   setDark: state.setDark,
-   dark: state.dark,
- }));

// After (FIXED)
+ const setDark = useDarkStore((state) => state.setDark);
+ const dark = useDarkStore((state) => state.dark);
```

**Result:** Application works perfectly, no more infinite loops!

#### Additional Rules for Zustand

1. **Never mutate store state directly**
   ```typescript
   // ❌ WRONG
   const state = useMyStore();
   state.value = 'new value';

   // ✅ CORRECT
   const setValue = useMyStore((state) => state.setValue);
   setValue('new value');
   ```

2. **Always include dependencies in useEffect**
   ```typescript
   const setDark = useDarkStore((state) => state.setDark);

   // ❌ WRONG - missing setDark dependency
   useEffect(() => {
     setDark(true);
   }, []);

   // ✅ CORRECT - include all dependencies
   useEffect(() => {
     setDark(true);
   }, [setDark]);
   ```

3. **Store actions are stable references**
   ```typescript
   // Store actions (functions in the store) are stable
   // They won't cause re-renders even in dependency arrays
   const setValue = useMyStore((state) => state.setValue);
   // setValue reference never changes ✅
   ```

4. **Use ESLint to catch these bugs**
   ```json
   {
     "rules": {
       "react-hooks/exhaustive-deps": "warn"
     }
   }
   ```

#### How to Search for This Bug

If you suspect unstable selectors:

```bash
# Find all object literal selectors (potential bugs)
grep -rE "use\w+Store\(\(state\) => \(\{" src/frontend/src/

# Find destructuring without selectors (also wrong)
grep -rE "const \{ .+ \} = use\w+Store\(\)" src/frontend/src/
```

#### Prevention Checklist

Before committing Zustand code:

- [ ] Are you using single-value selectors?
- [ ] If using object selector, did you add `shallow` comparison?
- [ ] Are all useEffect dependencies included?
- [ ] Did you test in browser (no infinite loops)?
- [ ] Did you check React DevTools Profiler for excessive re-renders?

**Bottom line:** Always use single-value selectors unless you have a very good reason and explicitly use `shallow` comparison. This prevents 99% of Zustand-related bugs!

---

### API Integration

**Service Functions:**
```typescript
// services/api.ts
import { api } from '@/controllers/API';

export async function createFlow(flowData: FlowData) {
  const response = await api.post('/flows/', flowData);
  return response.data;
}

export async function getFlows() {
  const response = await api.get('/flows/');
  return response.data;
}
```

**Error Handling Hook:**
```typescript
// hooks/useApi.ts
import { useState, useCallback } from 'react';

export function useApi<T>(apiFunction: (...args: any[]) => Promise<T>) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const execute = useCallback(async (...args: any[]) => {
    try {
      setLoading(true);
      setError(null);
      const result = await apiFunction(...args);
      return result;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      throw err;
    } finally {
      setLoading(false);
    }
  }, [apiFunction]);

  return { execute, loading, error };
}
```

### React Flow Integration

**Flow Graph Component:**
```typescript
import ReactFlow, {
  Node,
  Edge,
  Controls,
  Background
} from 'reactflow';

interface FlowGraphProps {
  nodes: Node[];
  edges: Edge[];
  onNodesChange: (changes: NodeChange[]) => void;
  onEdgesChange: (changes: EdgeChange[]) => void;
}

export function FlowGraph({
  nodes,
  edges,
  onNodesChange,
  onEdgesChange
}: FlowGraphProps) {
  return (
    <div className="w-full h-full">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        fitView
      >
        <Controls />
        <Background />
      </ReactFlow>
    </div>
  );
}
```

**Custom Node Types:**
```typescript
import { memo } from 'react';
import { Handle, Position } from 'reactflow';

interface ComponentNodeProps {
  data: {
    label: string;
    icon?: string;
  };
}

export const ComponentNode = memo(({ data }: ComponentNodeProps) => {
  return (
    <div className="px-4 py-2 shadow-md rounded-md bg-white border">
      <Handle type="target" position={Position.Top} />

      <div className="flex items-center">
        {data.icon && (
          <img src={data.icon} alt="" className="w-4 h-4 mr-2" />
        )}
        <span className="text-sm">{data.label}</span>
      </div>

      <Handle type="source" position={Position.Bottom} />
    </div>
  );
});
```

### Styling with Tailwind

**Component Styling:**
```typescript
import { cn } from '@/utils/cn';

interface ButtonProps {
  variant?: 'primary' | 'secondary';
  size?: 'sm' | 'md' | 'lg';
  children: React.ReactNode;
  onClick?: () => void;
}

export function Button({
  variant = 'primary',
  size = 'md',
  children,
  onClick
}: ButtonProps) {
  return (
    <button
      className={cn(
        'rounded-md font-medium transition-colors',
        {
          'bg-blue-600 hover:bg-blue-700 text-white': variant === 'primary',
          'bg-gray-200 hover:bg-gray-300 text-gray-900': variant === 'secondary',
          'px-2 py-1 text-sm': size === 'sm',
          'px-4 py-2 text-base': size === 'md',
          'px-6 py-3 text-lg': size === 'lg',
        }
      )}
      onClick={onClick}
    >
      {children}
    </button>
  );
}
```

**Dark Mode Support:**
```typescript
import { useDarkStore } from '@/stores/darkStore';

export function useDarkMode() {
  const { dark, setDark } = useDarkStore();

  const toggle = () => setDark(!dark);

  return { isDark: dark, toggle };
}
```

### Frontend Code Quality Workflow

```bash
# 1. Format code
make format_frontend

# 2. Run linting
make lint

# 3. Test in browser
# 4. Commit changes
```

### Build and Deployment

```bash
# Development build
make build_frontend

# Production build (creates dist/ directory)
cd src/frontend
npm run build
```

---

## Testing Guidelines

### Test Structure

**Backend Tests Location:**
- Unit Tests: `src/backend/tests/`
- Component Tests: `src/backend/tests/unit/components/` (organized by component subdirectory)

**Test File Naming:**
- Use same filename as component: `my_component.py` → `test_my_component.py`

### Built-in Fixtures & Base Classes

**`client` Fixture (FastAPI Test Client):**
- Defined in `src/backend/tests/conftest.py`
- Provides async `httpx.AsyncClient` connected to full application
- Automatically configured with in-memory SQLite database
- Skip with `@pytest.mark.noclient`

**Example:**
```python
async def test_login_endpoint(client):
    response = await client.post(
        "api/v1/login",
        data={"username": "foo", "password": "bar"}
    )
    assert response.status_code == 200
```

### ComponentTestBase Family

Located in `src/backend/tests/base.py`

| Base Class | Creates `client`? | Typical Use |
|------------|------------------|-------------|
| `ComponentTestBase` | No | Core logic for component version testing |
| `ComponentTestBaseWithClient` | Yes | Components needing API access during `run()` |
| `ComponentTestBaseWithoutClient` | No | Pure-logic components with no API calls |

**Required Fixtures:**
1. `component_class` → the component class under test
2. `default_kwargs` → dict of kwargs to instantiate component
3. `file_names_mapping` → list of `VersionComponentMapping` for version compatibility

**Example:**
```python
from tests.base import ComponentTestBaseWithClient, VersionComponentMapping, DID_NOT_EXIST
from langflow.components.my_namespace import MyComponent

class TestMyComponent(ComponentTestBaseWithClient):
    @pytest.fixture
    def component_class(self):
        return MyComponent

    @pytest.fixture
    def default_kwargs(self):
        return {"foo": "bar"}

    @pytest.fixture
    def file_names_mapping(self):
        return [
            VersionComponentMapping(
                version="1.1.1",
                module="my_module",
                file_name="my_component.py"
            ),
            VersionComponentMapping(
                version="1.0.19",
                module="my_module",
                file_name=DID_NOT_EXIST
            ),
        ]
```

### Component Testing Requirements

**Minimum Testing Requirements:**
- Create comprehensive unit tests for all new components
- If unit tests incomplete, create Markdown file with manual testing steps
  - Location: Same directory as unit tests
  - Filename: Same as component with `.md` extension

**Testing Best Practices:**
- Test both sync and async code paths
- Mock external dependencies appropriately
- Test error handling and edge cases
- Validate input/output behavior
- Test component initialization and configuration

### Async Testing Patterns

**Async Component Testing:**
```python
import pytest
import asyncio

@pytest.mark.asyncio
async def test_async_component():
    result = await component.async_method()
    assert result is not None
```

**Testing Background Tasks:**
```python
@pytest.mark.asyncio
async def test_background_task_completion():
    task = asyncio.create_task(component.background_operation())
    result = await asyncio.wait_for(task, timeout=5.0)
    assert result.success
```

**Testing Queue Operations:**
```python
@pytest.mark.asyncio
async def test_queue_operations():
    queue = asyncio.Queue()
    queue.put_nowait(test_data)
    result = await asyncio.wait_for(queue.get(), timeout=1.0)
    assert result == test_data
```

### Langflow-Specific Testing Patterns

**Message Testing:**
```python
from langflow.schema.message import Message

async def test_message_response(self, component_class, default_kwargs):
    component = component_class(**default_kwargs)
    message = await component.message_response()

    assert isinstance(message, Message)
    assert message.text == default_kwargs["input_value"]
    assert message.sender == default_kwargs["sender"]
```

**Flow Testing with JSON Data:**
```python
from tests.unit.build_utils import create_flow, build_flow, get_build_events

async def test_flow_execution(client, json_memory_chatbot_no_llm, logged_in_headers):
    flow_id = await create_flow(client, json_memory_chatbot_no_llm, logged_in_headers)
    build_response = await build_flow(client, flow_id, logged_in_headers)
    job_id = build_response["job_id"]

    events_response = await get_build_events(client, job_id, logged_in_headers)
    assert events_response.status_code == codes.OK
```

**External API Testing:**
```python
@pytest.mark.api_key_required
@pytest.mark.no_blockbuster
async def test_component_with_external_api(self):
    api_key = os.getenv("OPENAI_API_KEY")
    component = MyAPIComponent(
        api_key=api_key,
        model_name="gpt-4o",
        input_value="test input",
        session_id=str(uuid4()),
    )
    response = await component.message_response()
    assert response.data.get("text") is not None
```

**Mocking Language Models:**
```python
from tests.unit.mock_language_model import MockLanguageModel

@pytest.fixture
def default_kwargs(self):
    return {
        "agent_llm": MockLanguageModel(),
        "input_value": "test message",
        "session_id": str(uuid4()),
    }
```

### Test Execution

```bash
# Run all backend unit tests
make unit_tests

# Run specific test file
uv run pytest src/backend/tests/unit/test_specific_component.py

# Run specific test method
uv run pytest src/backend/tests/unit/test_component.py::test_specific_method

# Run with verbose output
uv run pytest -v src/backend/tests/unit/
```

### Special Testing Considerations

- Use `@pytest.mark.no_blockbuster` to skip blockbuster plugin
- Database tests may fail in batch runs but pass individually
- Context variables may not propagate correctly in `asyncio.to_thread`
- Test both direct event loop execution and thread scenarios

### Documentation in Tests

**Well-Documented Test Example:**
```python
async def test_component_background_processing():
    """
    Test that component processes items in background without blocking.

    This test verifies:
    1. Items are added to processing queue immediately
    2. Background processing completes successfully
    3. No deadlocks occur during shutdown
    4. All tasks are properly cleaned up
    """
    component = BackgroundComponent()
    await component.start()

    try:
        for i in range(10):
            await component.add_item(f"item_{i}")

        assert component.queue_size() == 10
        await component.wait_for_completion(timeout=5.0)
        assert component.processed_count() == 10
    finally:
        await component.stop()
        assert component.is_stopped()
```

---

## Component Creation

### Requirements Gathering

Before creating a component, gather:
- **Component Name:** What should it be called?
- **Description:** What does it do?
- **Inputs:** Required inputs (text, dropdown, boolean, etc.)
- **Outputs:** What should it output?
- **Category:** Which component category? (`src/backend/base/langflow/components/`)

### Component Definition Steps

1. **Inherit from `Component`**
2. **Set display properties:** `display_name`, `description`, `icon`
3. **Define inputs:** List of input field objects (`DropdownInput`, `MessageTextInput`, etc.)
4. **Define outputs:** List of `Output` objects
5. **Implement main logic** as methods

### Example: Conditional Router Component

```python
from langflow.components.base import Component
from langflow.inputs import MessageTextInput, DropdownInput
from langflow.schema import Output, Message

class ConditionalRouterComponent(Component):
    display_name = "If-Else"
    description = "Routes an input message to a corresponding output based on text comparison."
    icon = "split"
    name = "ConditionalRouter"

    inputs = [
        MessageTextInput(
            name="input_message",
            display_name="Input Message",
            info="The message to evaluate",
            required=True,
        ),
        DropdownInput(
            name="operator",
            display_name="Operator",
            options=["equals", "contains", "starts_with", "ends_with"],
            value="equals",
            info="Comparison operator to use",
        ),
        MessageTextInput(
            name="compare_text",
            display_name="Compare Text",
            info="Text to compare against",
            required=True,
        ),
    ]

    outputs = [
        Output(
            name="true_output",
            display_name="True Output",
            method="true_response",
        ),
        Output(
            name="false_output",
            display_name="False Output",
            method="false_response",
        ),
    ]

    def evaluate_condition(self) -> bool:
        """Evaluate the conditional logic."""
        input_text = self.input_message.text
        compare_text = self.compare_text

        if self.operator == "equals":
            return input_text == compare_text
        elif self.operator == "contains":
            return compare_text in input_text
        elif self.operator == "starts_with":
            return input_text.startswith(compare_text)
        elif self.operator == "ends_with":
            return input_text.endswith(compare_text)
        return False

    async def true_response(self) -> Message:
        """Return message when condition is true."""
        if self.evaluate_condition():
            return self.input_message
        return Message(text="")

    async def false_response(self) -> Message:
        """Return message when condition is false."""
        if not self.evaluate_condition():
            return self.input_message
        return Message(text="")
```

### Adding Component Icons

#### Backend (Python) - Setting Icon Name

In your component class:
```python
icon = "AstraDB"  # Must match frontend icon mapping exactly (case-sensitive)
```

For standard icons, use [Lucide icons](https://lucide.dev/icons) (e.g., `"clock"`, `"split"`, `"database"`)

#### Frontend (React/TypeScript) - Adding Custom Icon

**1. Create Icon Component** in `src/frontend/src/icons/AstraDB/`

**AstraDB.jsx:**
```jsx
const AstraSVG = (props) => (
  <svg {...props}>
    <path
      fill={props.isDark ? "#ffffff" : "#0A0A0A"}
      // ... SVG path data
    />
  </svg>
);
```

**index.tsx:**
```tsx
import React, { forwardRef } from "react";
import AstraSVG from "./AstraDB";

export const AstraDBIcon = forwardRef<
  SVGSVGElement,
  React.PropsWithChildren<{}>
>((props, ref) => {
  return <AstraSVG ref={ref} isDark={isDark} {...props} />;
});
```

**2. Add to Lazy Icon Imports** in `src/frontend/src/icons/lazyIconImports.ts`

```typescript
AstraDB: () =>
  import("@/icons/AstraDB").then((mod) => ({ default: mod.AstraDBIcon })),
```

### Component Best Practices

- Use clear and descriptive names for inputs and outputs
- Provide helpful `info` for each input to guide users
- Handle errors gracefully with meaningful error messages
- Use appropriate icons to visually represent function
- Support both light and dark mode for custom icons (use `isDark` prop)
- Implement proper async patterns for I/O operations
- Add comprehensive unit tests

---

## Internationalization (i18n)

### Overview

Langflow uses a **dual i18n system**:

1. **Backend (Python)**: Uses the `i18n` library for component metadata translation
2. **Frontend (React)**: Uses `i18next` with `react-i18next` for UI translation

**Supported Languages:**
- English (en) - Default fallback
- Chinese (zh) - Default language

### Backend i18n (Python Components)

#### Backend Configuration

**Location:** `src/lfx/src/lfx/locale/__init__.py`

```python
from pathlib import Path
import i18n

default_lang = "zh"  # Default language is Chinese

# i18n configuration
i18n.set("file_format", "json")
i18n.set("locale", default_lang)
i18n.set("fallback", default_lang)
i18n.set("use_locale_dirs", True)
i18n.set("filename_format", "{namespace}.{format}")
i18n.set("skip_locale_root_data", True)
i18n.load_path.append(str(Path(__file__).parent.resolve() / "translations"))

# Helper functions
def set_lang(locale: str):
    """Change the current language."""
    i18n.set("locale", locale)

def get_lang():
    """Get the current language."""
    return i18n.get("locale")

def get(key: str):
    """Get a translation by key."""
    return i18n.t(key)
```

#### Translation File Structure

**Directory Structure:**
```
src/lfx/src/lfx/locale/translations/
├── en/                          # English translations
│   └── components/
│       ├── agents/
│       ├── data/
│       ├── processing/
│       ├── tools/
│       ├── helpers/
│       ├── logic/
│       └── models/
└── zh/                          # Chinese translations
    └── components/
        ├── agents/
        ├── data/
        ├── processing/
        ├── tools/
        ├── helpers/
        ├── logic/
        └── models/
```

**Total Coverage:** 662+ translation JSON files across all component categories

#### Backend Component Example

**Component File:** `src/lfx/src/lfx/components/tools/calculator.py`

```python
import i18n
from lfx.base.langchain_utilities.model import LCToolComponent
from lfx.inputs.inputs import MessageTextInput
from lfx.template.field.base import Output

class CalculatorToolComponent(LCToolComponent):
    display_name = i18n.t("components.tools.calculator.display_name")
    description = i18n.t("components.tools.calculator.description")
    icon = "calculator"
    name = "CalculatorTool"

    inputs = [
        MessageTextInput(
            name="expression",
            display_name=i18n.t("components.tools.calculator.expression.display_name"),
            info=i18n.t("components.tools.calculator.expression.info"),
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t("components.tools.calculator.outputs.result.display_name"),
            name="result",
            method="calculate",
        ),
    ]

    def calculate(self):
        """Calculate the expression."""
        try:
            result = eval(self.expression)
            self.status = i18n.t("components.tools.calculator.success.calculation_completed",
                                 expression=self.expression, result=result)
            return result
        except ZeroDivisionError:
            raise ValueError(i18n.t("components.tools.calculator.errors.division_by_zero"))
        except Exception as e:
            raise ValueError(i18n.t("components.tools.calculator.errors.invalid_expression",
                                   error=str(e)))
```

**English Translation:** `src/lfx/src/lfx/locale/translations/en/components/tools/calculator.json`

```json
{
  "display_name": "Calculator",
  "description": "Perform basic arithmetic operations on a given expression.",
  "expression": {
    "display_name": "Expression",
    "info": "The arithmetic expression to evaluate (e.g., '4*4*(33/22)+12-20')."
  },
  "outputs": {
    "result": {
      "display_name": "Result"
    }
  },
  "success": {
    "calculation_completed": "Calculation completed: {expression} = {result}"
  },
  "errors": {
    "function_calls_not_supported": "Function calls like sqrt(), sin(), cos() etc. are not supported.",
    "invalid_expression": "Invalid expression: {error}",
    "division_by_zero": "Error: Division by zero"
  }
}
```

**Chinese Translation:** `src/lfx/src/lfx/locale/translations/zh/components/tools/calculator.json`

```json
{
  "display_name": "计算器",
  "description": "对给定表达式执行基本算术运算。",
  "expression": {
    "display_name": "表达式",
    "info": "要计算的算术表达式（例如：'4*4*(33/22)+12-20'）。"
  },
  "outputs": {
    "result": {
      "display_name": "结果"
    }
  },
  "success": {
    "calculation_completed": "计算完成：{expression} = {result}"
  },
  "errors": {
    "function_calls_not_supported": "不支持函数调用，如sqrt()、sin()、cos()等。",
    "invalid_expression": "无效表达式：{error}",
    "division_by_zero": "错误：除以零"
  }
}
```

#### Complex Backend Example

**Component with Multiple Inputs:** `src/lfx/src/lfx/components/processing/llm_router.py`

```python
import i18n
from lfx.custom.custom_component.component import Component
from lfx.inputs.inputs import DropdownInput, HandleInput, MultilineInput

class LLMRouterComponent(Component):
    display_name = i18n.t("components.processing.llm_router.display_name")
    description = i18n.t("components.processing.llm_router.description")
    icon = "git-branch"

    inputs = [
        HandleInput(
            name="models",
            display_name=i18n.t("components.processing.llm_router.models.display_name"),
            input_types=["LanguageModel"],
            required=True,
            is_list=True,
            info=i18n.t("components.processing.llm_router.models.info"),
        ),
        MultilineInput(
            name="input_value",
            display_name=i18n.t("components.processing.llm_router.input_value.display_name"),
            required=True,
            info=i18n.t("components.processing.llm_router.input_value.info"),
        ),
        DropdownInput(
            name="optimization",
            display_name=i18n.t("components.processing.llm_router.optimization.display_name"),
            options=[
                i18n.t("components.processing.llm_router.optimization.quality"),
                i18n.t("components.processing.llm_router.optimization.speed"),
                i18n.t("components.processing.llm_router.optimization.cost"),
                i18n.t("components.processing.llm_router.optimization.balanced"),
            ],
            value=i18n.t("components.processing.llm_router.optimization.balanced"),
            info=i18n.t("components.processing.llm_router.optimization.info"),
        ),
    ]
```

**Translation with Nested Keys:** `en/components/processing/llm_router.json`

```json
{
  "display_name": "LLM Router",
  "description": "Routes the input to the most appropriate LLM based on OpenRouter model specifications",
  "models": {
    "display_name": "Language Models",
    "info": "List of LLMs to route between"
  },
  "input_value": {
    "display_name": "Input",
    "info": "The input message to be routed"
  },
  "optimization": {
    "display_name": "Optimization",
    "info": "Optimization preference for model selection",
    "quality": "quality",
    "speed": "speed",
    "cost": "cost",
    "balanced": "balanced"
  },
  "outputs": {
    "output": {
      "display_name": "Output"
    }
  },
  "errors": {
    "missing_required_inputs": "Missing required inputs: models, input_value, or judge_llm",
    "routing_error": "Routing error: {error_type} - {error}"
  },
  "status": {
    "fetching_openrouter_specs": "Fetching OpenRouter model specifications...",
    "analyzing_models": "Analyzing available models and preparing specifications..."
  }
}
```

#### Backend Translation Best Practices

1. **Import i18n at the top:**
   ```python
   import i18n
   ```

2. **Use dot notation for keys:**
   ```python
   # Format: components.{category}.{component_name}.{field}.{subfield}
   display_name = i18n.t("components.processing.my_component.display_name")
   ```

3. **Support string interpolation:**
   ```python
   # In Python code
   message = i18n.t("components.tools.calculator.success.result",
                    value=result, count=5)

   # In JSON
   {
     "success": {
       "result": "Processed {count} items with result: {value}"
     }
   }
   ```

4. **Organize by message type:**
   - `display_name` and `description` at root level
   - Input/output info nested under field names
   - `errors`, `success`, `status`, `warnings` as separate objects

#### Recommended Translation JSON Structure

```json
{
  "display_name": "Component Name",
  "description": "Component description",

  "input_field_name": {
    "display_name": "Input Display Name",
    "info": "Information about the input"
  },

  "outputs": {
    "output_name": {
      "display_name": "Output Name",
      "info": "Output description"
    }
  },

  "success": {
    "action_completed": "Action completed successfully: {details}"
  },

  "errors": {
    "error_type": "Error message: {error_details}",
    "another_error": "Another error occurred"
  },

  "status": {
    "processing": "Processing {item}...",
    "complete": "Processing complete"
  },

  "warnings": {
    "warning_type": "Warning message"
  }
}
```

### Frontend i18n (React Components)

#### Frontend Configuration

**Libraries Used:**
- `i18next` - Core i18n framework
- `react-i18next` - React bindings
- `i18next-browser-languagedetector` - Auto language detection
- `i18next-http-backend` - Load translations from server

**Configuration File:** `src/frontend/src/i18n.ts`

```typescript
import i18n from "i18next";
import LanguageDetector from "i18next-browser-languagedetector";
import Backend from "i18next-http-backend";
import { initReactI18next } from "react-i18next";

i18n
  // Load translation using HTTP
  .use(Backend)
  // Detect user language
  .use(LanguageDetector)
  // Pass the i18n instance to react-i18next
  .use(initReactI18next)
  // Initialize i18next
  .init({
    fallbackLng: "en",
    debug: false,
    interpolation: {
      escapeValue: false, // React already does escaping
    },
    backend: {
      loadPath: "/locales/{{lng}}/{{ns}}.json",
    },
    detection: {
      order: ["localStorage", "navigator", "htmlTag"],
      caches: ["localStorage"],  // Remember user's language preference
    },
  });

export default i18n;
```

#### Frontend Language Store

**Store File:** `src/frontend/src/stores/i18nStore.ts`

```typescript
import { create } from "zustand";
import { I18nType } from "@/types/zustand/i18n";

export const useI18nStore = create<I18nType>((set, get) => ({
  lang: (() => {
    const stored = window.localStorage.getItem("language");
    if (stored !== null) {
      return JSON.parse(stored);
    }
    return 'zh';  // Default to Chinese
  })(),

  setLanguage(lang) {
    window.localStorage.setItem("language", JSON.stringify(lang));
    set({ lang });
  },
}));
```

#### Frontend Translation Files

**Location:** `src/frontend/public/locales/`

```
public/locales/
├── en/
│   └── translation.json     # English UI translations
└── zh/
    └── translation.json     # Chinese UI translations
```

**English Translation:** `public/locales/en/translation.json`

```json
{
  "common": {
    "settings": "Settings",
    "version": "Version",
    "logout": "Logout",
    "login": "Login",
    "signup": "Sign Up",
    "cancel": "Cancel",
    "save": "Save",
    "delete": "Delete",
    "edit": "Edit",
    "create": "Create",
    "update": "Update",
    "search": "Search",
    "filter": "Filter",
    "loading": "Loading...",
    "error": "Error",
    "success": "Success",
    "warning": "Warning",
    "language": "Language",
    "english": "English",
    "chinese": "中文"
  },
  "flows": {
    "createNew": "Create New Flow",
    "editFlow": "Edit Flow",
    "deleteFlow": "Delete Flow",
    "exportFlow": "Export Flow",
    "importFlow": "Import Flow"
  },
  "components": {
    "addComponent": "Add Component",
    "removeComponent": "Remove Component",
    "configureComponent": "Configure Component"
  }
}
```

**Chinese Translation:** `public/locales/zh/translation.json`

```json
{
  "common": {
    "settings": "设置",
    "version": "版本",
    "logout": "退出登录",
    "login": "登录",
    "signup": "注册",
    "cancel": "取消",
    "save": "保存",
    "delete": "删除",
    "edit": "编辑",
    "create": "创建",
    "update": "更新",
    "search": "搜索",
    "filter": "筛选",
    "loading": "加载中...",
    "error": "错误",
    "success": "成功",
    "warning": "警告",
    "language": "语言",
    "english": "English",
    "chinese": "中文"
  },
  "flows": {
    "createNew": "创建新流程",
    "editFlow": "编辑流程",
    "deleteFlow": "删除流程",
    "exportFlow": "导出流程",
    "importFlow": "导入流程"
  },
  "components": {
    "addComponent": "添加组件",
    "removeComponent": "移除组件",
    "configureComponent": "配置组件"
  }
}
```

#### Frontend Component Usage

**App-Level Language Switching:** `src/frontend/src/App.tsx`

```typescript
import { useTranslation } from 'react-i18next';
import { useI18nStore } from './stores/i18nStore';

export default function App() {
  const lang = useI18nStore((state) => state.lang);
  const { i18n } = useTranslation();

  useEffect(() => {
    if (lang) {
      i18n.changeLanguage(lang);  // Update language when store changes
    }
  }, [lang, i18n]);

  return (
    <RouterProvider router={router} />
  );
}
```

**Component-Level Usage:**

```typescript
import { useTranslation } from "react-i18next";

export default function MyComponent() {
  const { t } = useTranslation();  // Get translation function

  return (
    <div>
      <h1>{t('common.settings')}</h1>
      <button>{t('common.save')}</button>
      <button>{t('common.cancel')}</button>

      {/* With interpolation */}
      <p>{t('flows.itemCount', { count: 5 })}</p>
    </div>
  );
}
```

**Language Switcher Component:**

```typescript
import { useTranslation } from "react-i18next";
import { useI18nStore } from "@/stores/i18nStore";

export function LanguageSwitcher() {
  const { t, i18n } = useTranslation();
  const { setLanguage } = useI18nStore();

  const handleLanguageChange = (lang: string) => {
    setLanguage(lang);
    i18n.changeLanguage(lang);
  };

  return (
    <select
      value={i18n.language}
      onChange={(e) => handleLanguageChange(e.target.value)}
    >
      <option value="en">{t('common.english')}</option>
      <option value="zh">{t('common.chinese')}</option>
    </select>
  );
}
```

### Adding Translations for New Components

#### Step 1: Create Backend Component with i18n

**File:** `src/lfx/src/lfx/components/processing/my_component.py`

```python
import i18n
from lfx.custom.custom_component.component import Component
from lfx.inputs.inputs import MessageTextInput, DropdownInput
from lfx.template.field.base import Output

class MyNewComponent(Component):
    display_name = i18n.t("components.processing.my_component.display_name")
    description = i18n.t("components.processing.my_component.description")
    icon = "my-icon"

    inputs = [
        MessageTextInput(
            name="input_text",
            display_name=i18n.t("components.processing.my_component.input_text.display_name"),
            info=i18n.t("components.processing.my_component.input_text.info"),
            required=True,
        ),
        DropdownInput(
            name="mode",
            display_name=i18n.t("components.processing.my_component.mode.display_name"),
            options=[
                i18n.t("components.processing.my_component.mode.fast"),
                i18n.t("components.processing.my_component.mode.accurate"),
            ],
            value=i18n.t("components.processing.my_component.mode.fast"),
            info=i18n.t("components.processing.my_component.mode.info"),
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t("components.processing.my_component.outputs.result.display_name"),
            name="result",
            method="process",
        ),
    ]

    def process(self):
        """Process the input."""
        try:
            result = self.do_processing()
            self.status = i18n.t("components.processing.my_component.success.completed",
                                 count=len(result))
            return result
        except Exception as e:
            raise ValueError(i18n.t("components.processing.my_component.errors.processing_failed",
                                   error=str(e)))
```

#### Step 2: Create English Translation

**File:** `src/lfx/src/lfx/locale/translations/en/components/processing/my_component.json`

```json
{
  "display_name": "My Component",
  "description": "Description of what my component does",

  "input_text": {
    "display_name": "Input Text",
    "info": "The text input to process"
  },

  "mode": {
    "display_name": "Processing Mode",
    "info": "Select the processing mode",
    "fast": "fast",
    "accurate": "accurate"
  },

  "outputs": {
    "result": {
      "display_name": "Result",
      "info": "The processed result"
    }
  },

  "success": {
    "completed": "Successfully processed {count} items"
  },

  "errors": {
    "processing_failed": "Processing failed: {error}",
    "invalid_input": "Invalid input provided"
  },

  "status": {
    "processing": "Processing input...",
    "validating": "Validating data..."
  }
}
```

#### Step 3: Create Chinese Translation

**File:** `src/lfx/src/lfx/locale/translations/zh/components/processing/my_component.json`

```json
{
  "display_name": "我的组件",
  "description": "我的组件的功能描述",

  "input_text": {
    "display_name": "输入文本",
    "info": "要处理的文本输入"
  },

  "mode": {
    "display_name": "处理模式",
    "info": "选择处理模式",
    "fast": "快速",
    "accurate": "精确"
  },

  "outputs": {
    "result": {
      "display_name": "结果",
      "info": "处理后的结果"
    }
  },

  "success": {
    "completed": "成功处理了{count}个项目"
  },

  "errors": {
    "processing_failed": "处理失败：{error}",
    "invalid_input": "提供了无效输入"
  },

  "status": {
    "processing": "正在处理输入...",
    "validating": "正在验证数据..."
  }
}
```

#### Step 4: Add Frontend Translations (if needed)

If your component requires UI-specific translations, add to frontend translation files:

**File:** `src/frontend/public/locales/en/translation.json`

```json
{
  "myComponent": {
    "title": "My Component",
    "configure": "Configure Component",
    "tooltip": "This component processes text input"
  }
}
```

**File:** `src/frontend/public/locales/zh/translation.json`

```json
{
  "myComponent": {
    "title": "我的组件",
    "configure": "配置组件",
    "tooltip": "此组件处理文本输入"
  }
}
```

### i18n Utility Tools

#### Backend Utility Functions

**Location:** `src/lfx/src/lfx/locale/__init__.py`

```python
from lfx.locale import set_lang, get_lang, get

# Change language programmatically
set_lang("en")  # Switch to English
set_lang("zh")  # Switch to Chinese

# Get current language
current_language = get_lang()  # Returns "en" or "zh"

# Get a translation directly (alternative to i18n.t())
translation = get("components.processing.my_component.display_name")
```

#### Translation Validation Script

**Location:** `src/lfx/src/lfx/fix_i18n.py`

This utility script helps maintain translation completeness:
- Extracts all `i18n.t()` calls from component files
- Ensures both English and Chinese translation files have all required keys
- Generates missing keys with sensible defaults
- Validates nested key structures

**Usage:**
```bash
cd src/lfx/src/lfx
python fix_i18n.py
```

### Language Detection & Persistence

#### Frontend Language Detection

The frontend uses i18next's language detection in this priority order:

1. **localStorage**: Saved user preference (persists across sessions)
2. **navigator**: Browser's default language
3. **htmlTag**: HTML `lang` attribute

**Detection Configuration:**
```typescript
detection: {
  order: ["localStorage", "navigator", "htmlTag"],
  caches: ["localStorage"],  // Persist user's choice
}
```

#### Backend Language Setting

Backend defaults to Chinese but can be changed:

```python
from lfx.locale import set_lang

# At application startup or per-request
set_lang("en")  # English
set_lang("zh")  # Chinese
```

### i18n Best Practices

#### General Guidelines

1. **Use consistent key naming:**
   - Backend: `components.{category}.{component_name}.{field}`
   - Frontend: `{section}.{subsection}.{key}`

2. **Organize by category:**
   - Separate translation files for each component
   - Group related translations together

3. **Include all message types:**
   - Display names and descriptions
   - Input/output info
   - Error messages
   - Success messages
   - Status updates
   - Warnings

4. **Use placeholders for dynamic content:**
   ```python
   # Python
   i18n.t("errors.failed", error=str(e), count=5)

   # TypeScript
   t('errors.failed', { error: e.message, count: 5 })

   # JSON
   {
     "errors": {
       "failed": "Failed with error {error} after {count} attempts"
     }
   }
   ```

5. **Keep translations in sync:**
   - Both EN and ZH files should have identical structure
   - Run validation scripts regularly
   - Test in both languages

6. **Avoid hardcoding strings:**
   ```python
   # Bad
   display_name = "My Component"

   # Good
   display_name = i18n.t("components.processing.my_component.display_name")
   ```

7. **Use nested JSON structure:**
   ```json
   {
     "field_name": {
       "display_name": "Field Name",
       "info": "Field description",
       "options": {
         "option1": "First Option",
         "option2": "Second Option"
       }
     }
   }
   ```

8. **Document complex translations:**
   ```json
   {
     "_comment": "This translation is used in the context menu",
     "menu_item": "Delete Selected Items"
   }
   ```

9. **Test both languages thoroughly:**
   - Verify UI layout in both languages
   - Check for text overflow issues
   - Ensure translations are contextually appropriate

10. **Handle pluralization:**
    ```typescript
    // Frontend with react-i18next
    t('items', { count: 1 })  // "1 item"
    t('items', { count: 5 })  // "5 items"

    // JSON
    {
      "items_one": "{{count}} item",
      "items_other": "{{count}} items"
    }
    ```

#### Development Workflow

1. **Write component code with i18n calls**
2. **Create English translation file**
3. **Create Chinese translation file** (or use translation service)
4. **Run validation script** to check completeness
5. **Test in both languages**
6. **Format and lint code**
7. **Commit changes**

### i18n Development Checklist

**Backend Component i18n:**
- [ ] Import `i18n` at top of component file
- [ ] Use `i18n.t()` for all user-facing strings
- [ ] Create English translation JSON file
- [ ] Create Chinese translation JSON file
- [ ] Use consistent key naming convention
- [ ] Include all message types (errors, success, status)
- [ ] Support string interpolation where needed
- [ ] Test component in both languages
- [ ] Run `fix_i18n.py` to validate

**Frontend Component i18n:**
- [ ] Import `useTranslation` hook
- [ ] Use `t()` function for all UI text
- [ ] Add translations to `en/translation.json`
- [ ] Add translations to `zh/translation.json`
- [ ] Test UI in both languages
- [ ] Check for layout issues with longer translations
- [ ] Verify language switching works correctly
- [ ] Test localStorage persistence

**Translation Quality:**
- [ ] Translations are contextually appropriate
- [ ] Grammar and spelling are correct
- [ ] Consistent terminology across components
- [ ] Placeholders work correctly
- [ ] No hardcoded strings remain
- [ ] Both language files have identical structure
- [ ] Complex translations are documented

---

## Documentation Development

### Documentation Structure

```
docs/
├── docs/                    # Main documentation content
│   ├── agents/              # Agent and MCP guides
│   ├── get-started/         # Getting started guides
│   ├── tutorials/           # Langflow tutorials
│   ├── components/          # Component documentation
│   ├── flows/               # Flow guides
│   ├── deployment/          # Deployment guides
│   ├── develop/             # Development guides
│   ├── support/             # Help and release notes
│   ├── contributing/        # Contribution guidelines
│   └── api-reference/       # API documentation
├── src/                     # Custom React components
├── static/                  # Static assets (images, etc.)
├── sidebars.js             # Sidebar configuration
├── docusaurus.config.js    # Main configuration
└── package.json            # Dependencies
```

### Documentation Service

```bash
cd docs
yarn install      # Install dependencies
yarn start        # Start dev server (usually port 3001)
```

Access at: http://localhost:3001/

### Component Documentation Template

```markdown
---
title: Component Name
description: Brief description of what the component does
sidebar_position: 1
---

# Component Name

Brief overview of the component's purpose.

## Overview

What this component does and when to use it.

## Configuration

### Inputs

| Input | Type | Required | Description |
|-------|------|----------|-------------|
| `input_text` | String | Yes | The text to process |
| `model_name` | String | No | Model to use (default: gpt-3.5-turbo) |

### Outputs

| Output | Type | Description |
|--------|------|-------------|
| `result` | Message | Processed result |

## Usage Example

```python
# Example of using the component
component = MyComponent(
    input_text="Hello, world!",
    model_name="gpt-4"
)
result = component.run()
```

## Common Issues

### Issue: Component not loading

**Solution:** Check that all required inputs are provided.
```

### Writing Style Guide

**Tone:** Professional but approachable
**Voice:** Second person ("you") for instructions
**Tense:** Present tense for current features
**Length:** Keep paragraphs short and scannable

**Formatting:**
- Headers: Use sentence case
- Code: Inline code with `backticks`
- Emphasis: Use **bold** for UI elements, *italic* for emphasis
- Lists: Use parallel structure

**Terminology:**
- **Langflow:** Always capitalize
- **Component:** Capitalize when referring to Langflow components
- **Flow:** Capitalize when referring to Langflow flows
- **API:** Always uppercase
- **JSON:** Always uppercase

### Documentation Build

```bash
cd docs
yarn build    # Build static site
yarn serve    # Serve built site locally
```

---

## Code Quality Standards

### Backend Quality Workflow

```bash
# CRITICAL: Run format FIRST (saves time on lint fixes)
make format_backend

# Then run linting
make lint

# Then run tests
make unit_tests

# Finally commit
```

### Frontend Quality Workflow

```bash
# Format code
make format_frontend

# Run linting
make lint

# Test in browser
# Commit changes
```

### Development Checklist

**Backend Component:**
- [ ] Component added to appropriate subdirectory
- [ ] `__init__.py` updated with alphabetical imports
- [ ] **All user-facing strings use `i18n.t()` (no hardcoded strings)**
- [ ] **English translation JSON file created in `src/lfx/src/lfx/locale/translations/en/`**
- [ ] **Chinese translation JSON file created in `src/lfx/src/lfx/locale/translations/zh/`**
- [ ] Code formatted with `make format_backend` (FIRST)
- [ ] Linting passed with `make lint`
- [ ] Unit tests created and passing with `make unit_tests`
- [ ] Component tested in UI with backend restart + browser refresh
- [ ] **Component tested in both English and Chinese**
- [ ] Version mapping provided for backward compatibility
- [ ] Async patterns implemented correctly with proper cleanup
- [ ] External API calls use appropriate pytest markers

**Frontend Component:**
- [ ] Frontend service running with `make frontend`
- [ ] Changes hot-reload correctly in browser
- [ ] State management uses Zustand stores
- [ ] API calls use proper error handling
- [ ] Components styled with Tailwind CSS
- [ ] Dark mode support implemented where needed
- [ ] **All UI text uses `t()` function from `useTranslation` hook**
- [ ] **Translations added to `public/locales/en/translation.json`**
- [ ] **Translations added to `public/locales/zh/translation.json`**
- [ ] Code formatted with `make format_frontend`
- [ ] Linting passed with `make lint`
- [ ] Changes tested in both light and dark mode
- [ ] **Changes tested in both English and Chinese**

**Component Icons:**
- [ ] Icon name decided (clear, descriptive)
- [ ] Python component has `icon = "IconName"` set
- [ ] Icon directory created in `src/frontend/src/icons/`
- [ ] SVG component created with `isDark` prop support
- [ ] `index.tsx` exports icon using `forwardRef`
- [ ] Icon added to `lazyIconImports.ts`
- [ ] Icon verified in UI (light and dark mode)

**Internationalization:**
- [ ] Backend component uses `i18n.t()` for all strings
- [ ] Translation files follow naming convention: `components.{category}.{name}.{field}`
- [ ] English translation JSON complete with all keys
- [ ] Chinese translation JSON complete with all keys
- [ ] Translation files have identical structure
- [ ] String interpolation tested (e.g., `{count}`, `{error}`)
- [ ] Error messages, success messages, and status messages translated
- [ ] Dropdown options and field labels translated
- [ ] Frontend uses `useTranslation` hook where applicable
- [ ] `fix_i18n.py` script run to validate translations
- [ ] Component tested in both languages
- [ ] No hardcoded user-facing strings remain

**Testing:**
- [ ] Unit tests created for all new components
- [ ] Async patterns tested appropriately
- [ ] Error handling and edge cases covered
- [ ] Manual testing documentation created (if tests incomplete)
- [ ] Background tasks and queues tested for proper cleanup
- [ ] Appropriate pytest markers used
- [ ] Tests well-documented with clear docstrings
- [ ] Resource cleanup properly handled in fixtures

**Documentation:**
- [ ] Documentation service running with `yarn start`
- [ ] Content follows markdown conventions
- [ ] Code examples tested and working
- [ ] Images have descriptive alt text
- [ ] Internal links functional
- [ ] Sidebar navigation updated
- [ ] Content follows style guide
- [ ] Build succeeds with `yarn build`

---

## Known Issues & Tips

### Backend
- **Database tests** may fail in batch runs but pass individually
- **Starter project files** auto-format after `langflow run` (can commit or ignore)
- **Context variables** may not propagate in `asyncio.to_thread` - test both patterns

### Frontend
- **Hot reload** should work automatically - if not, restart dev server
- **Dark mode** test all components in both modes
- **Build errors** check TypeScript types are correct

### Testing
- Use `@pytest.mark.noclient` to skip client creation when not needed
- Use `@pytest.mark.no_blockbuster` to skip blockbuster plugin
- Use `@pytest.mark.api_key_required` for tests requiring external APIs

---

## Quick Reference Commands

```bash
# Development
make backend                 # Start backend (port 7860)
make frontend                # Start frontend (port 3000)
make init                    # Full initialization

# Code Quality
make format_backend          # Format Python code (RUN FIRST!)
make format_frontend         # Format TypeScript/JavaScript code
make lint                    # Run all linting checks

# Testing
make unit_tests              # Run backend unit tests
make integration_tests       # Run integration tests
make tests_frontend          # Run frontend tests
make coverage                # Run tests with coverage

# Documentation
cd docs && yarn start        # Start docs dev server
cd docs && yarn build        # Build static docs site

# Internationalization
cd src/lfx/src/lfx && python fix_i18n.py  # Validate translation completeness

# Specific test execution
uv run pytest src/backend/tests/unit/test_file.py              # Run specific file
uv run pytest src/backend/tests/unit/test_file.py::test_method # Run specific test
uv run pytest -v src/backend/tests/unit/                       # Verbose output
```

---

**Last Updated:** 2025-10-17

This guide consolidates all development guidelines into a comprehensive reference for Claude Code when developing Langflow. Follow these guidelines to maintain code quality, consistency, and best practices across the project.
# Documentation Prefix Policy

## Naming Rule
- Format: `(Type) - Module - Document Title`
- Example: `(R) - User Login - User Login Requirements`

## Document Types
- (E) Error / Bug
- (R) Requirement
- (A) Architecture (overall system)
- (T) Test (test plan / unit tests)
- (D) Developer Design (detailed design)
- (I) Interface / API
- (O) Operation / Ops
- (M) Model / Data Model
- (ADR) Architecture Decision Record
- (S) Security
- (U) User Guide
- (P) Product
- (Q) Quality / Compliance

## Mandatory Metadata (All Docs)
- Doc ID: `DOC-YYYYMMDD-SEQ`
- Doc Type: E/R/A/T/D/I/O/M/ADR/S/U/P/Q
- Module/System
- Version + Status (Draft/Review/Approved/Deprecated)
- Author/Reviewer
- Created/Updated Date
- Related Docs (upstream/downstream)
- Scope (team/env)

## Common Sections (All Docs)
- Background & Purpose
- Scope & Out of Scope
- Constraints & Assumptions
- Risks & Open Questions
- Change Log

## Type-Specific Sections + Example Titles
- (E) Phenomenon, Repro Steps, Expected/Actual, Impact, Root Cause, Fix, Verification
  - Example: `(E) - Payments - Callback Timeout Analysis`
- (R) Business Goals, User Scenarios, Functional List, Non-Functional, Priority, Acceptance
  - Example: `(R) - User Login - Login Requirements`
- (A) System Boundary, Components, Data Flow, Tech Choices, Scalability/DR
  - Example: `(A) - Orders - Layered Architecture`
- (T) Scope, Strategy, Test Cases, Data Prep, Coverage, Risks
  - Example: `(T) - User Login - Test Plan`
- (D) Modules, Key Flows/Algorithms, Edge Handling, Complexity, Dependencies
  - Example: `(D) - User Login - Detailed Design`
- (I) API Contract, Request/Response, Errors, Auth, Idempotency/Rate Limits
  - Example: `(I) - User Login - API Spec`
- (O) Deployment, Monitoring/Alerting, Rollout/Rollback, Capacity
  - Example: `(O) - Orders - Ops Runbook`
- (M) ER/Table Design, Fields, Constraints, Indexes, Data Dictionary
  - Example: `(M) - Orders - Data Model`
- (ADR) Problem, Options, Decision, Trade-offs, Consequences
  - Example: `(ADR) - Orders - MQ Selection`
- (S) Threat Model, Access Control, Encryption, Audit, Mitigations
  - Example: `(S) - User Login - Security Design`
- (U) Audience, Steps, FAQs, Notes
  - Example: `(U) - User Login - User Guide`
- (P) Goals, Value Proposition, Target Users, Competitors, Roadmap
  - Example: `(P) - User Login - Product Plan`
- (Q) Quality Metrics, Compliance, Audits, Risk Controls
  - Example: `(Q) - Orders - Quality & Compliance`

## Mandatory Output Rule (AI)
- Every AI design/delivery must generate the relevant doc type(s).
- At least one primary doc (typically R/D/A).
- Produce related docs together (e.g., if APIs exist, also generate I; if data schema exists, also generate M).
- If a type is missing for the task, explicitly suggest adding it.

## Document Location (AI Required)
- All generated docs must be stored under `dev-docs/` at the project root.
- If `dev-docs/` does not exist, create it before writing.

## Language + Title Format (AI Required)
- Generated documents must be written in Chinese.
- The document title must include the type prefix, for example: `(D) - UI Avatar - 场景激活更新UI`.
