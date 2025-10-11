// src/constants/constants.ts

import { customDefaultShortcuts } from "@/customization/constants";
import custom from "../customization/config-constants";
import type { languageMap } from "../types/components";

/**
 * invalid characters for flow name
 * @constant
 */
export const INVALID_CHARACTERS = [
  " ",
  ",",
  ".",
  ":",
  ";",
  "!",
  "?",
  "/",
  "\\",
  "(",
  ")",
  "[",
  "]",
  "\n",
];

/**
 * regex to highlight the variables in the text
 * @constant regexHighlight
 * @type {RegExp}
 * @default
 * @example
 * {{variable}} or {variable}
 * @returns {RegExp}
 * @description
 * This regex is used to highlight the variables in the text.
 * It matches the variables in the text that are between {{}} or {}.
 */

/**
 *  p1 – fenced code block ```...```
 *  p2 – opening brace run (one or more)
 *  p3 – variable name  (no braces)
 *  p4 – closing brace run (one or more)
 */
export const regexHighlight = /(```[\s\S]*?```)|(\{+)([^{}]+)(\}+)/g;
export const specialCharsRegex = /[!@#$%^&*()\-_=+[\]{}|;:'",.<>/?\\`´]/;

export const programmingLanguages: languageMap = {
  javascript: ".js",
  python: ".py",
  java: ".java",
  c: ".c",
  cpp: ".cpp",
  "c++": ".cpp",
  "c#": ".cs",
  ruby: ".rb",
  php: ".php",
  swift: ".swift",
  "objective-c": ".m",
  kotlin: ".kt",
  typescript: ".ts",
  go: ".go",
  perl: ".pl",
  rust: ".rs",
  scala: ".scala",
  haskell: ".hs",
  lua: ".lua",
  shell: ".sh",
  sql: ".sql",
  html: ".html",
  css: ".css",
  // add more file extensions here, make sure the key is same as language prop in CodeBlock.tsx component
};
/**
 * Number maximum of components to scroll on tooltips
 * @constant
 */
export const MAX_LENGTH_TO_SCROLL_TOOLTIP = 200;

export const MESSAGES_TABLE_ORDER = [
  "timestamp",
  "message",
  "text",
  "sender",
  "sender_name",
  "session_id",
  "files",
];

/**
 * Number maximum of components to scroll on tooltips
 * @constant
 */
export const MAX_WORDS_HIGHLIGHT = 79;

/**
 * Limit of items before show scroll on fields modal
 * @constant
 */
export const limitScrollFieldsModal = 10;

/**
 * The base text for subtitle of code dialog
 * @constant
 */
export const COLUMN_DIV_STYLE =
  " w-full h-full flex overflow-auto flex-col bg-muted px-16 ";

export const NAV_DISPLAY_STYLE =
  " w-full flex justify-between py-12 pb-2 px-6 ";

/**
 * The base text for subtitle of code dialog
 * @constant
 */
export const DESCRIPTIONS: string[] = [
  "Chain the Words, Master Language!",
  "Language Architect at Work!",
  "Empowering Language Engineering.",
  "Craft Language Connections Here.",
  "Create, Connect, Converse.",
  "Smart Chains, Smarter Conversations.",
  "Bridging Prompts for Brilliance.",
  "Language Models, Unleashed.",
  "Your Hub for Text Generation.",
  "Promptly Ingenious!",
  "Building Linguistic Labyrinths.",
  "Langflow: Create, Chain, Communicate.",
  "Connect the Dots, Craft Language.",
  "Interactive Language Weaving.",
  "Generate, Innovate, Communicate.",
  "Conversation Catalyst Engine.",
  "Language Chainlink Master.",
  "Design Dialogues with Langflow.",
  "Nurture NLP Nodes Here.",
  "Conversational Cartography Unlocked.",
  "Design, Develop, Dialogize.",
];
export const BUTTON_DIV_STYLE =
  " flex gap-2 focus:ring-1 focus:ring-offset-1 focus:ring-ring focus:outline-none ";

/**
 * The base text for subtitle of code dialog
 * @constant
 */
export const ADJECTIVES: string[] = [
  "admiring",
  "adoring",
  "agitated",
  "amazing",
  "angry",
  "awesome",
  "backstabbing",
  "berserk",
  "big",
  "boring",
  "clever",
  "cocky",
  "compassionate",
  "condescending",
  "cranky",
  "desperate",
  "determined",
  "distracted",
  "dreamy",
  "drunk",
  "ecstatic",
  "elated",
  "elegant",
  "evil",
  "fervent",
  "focused",
  "furious",
  "gigantic",
  "gloomy",
  "goofy",
  "grave",
  "happy",
  "high",
  "hopeful",
  "hungry",
  "insane",
  "jolly",
  "jovial",
  "kickass",
  "lonely",
  "loving",
  "mad",
  "modest",
  "naughty",
  "nauseous",
  "nostalgic",
  "pedantic",
  "pensive",
  "prickly",
  "reverent",
  "romantic",
  "sad",
  "serene",
  "sharp",
  "sick",
  "silly",
  "sleepy",
  "small",
  "stoic",
  "stupefied",
  "suspicious",
  "tender",
  "thirsty",
  "tiny",
  "trusting",
  "bubbly",
  "charming",
  "cheerful",
  "comical",
  "dazzling",
  "delighted",
  "dynamic",
  "effervescent",
  "enthusiastic",
  "exuberant",
  "fluffy",
  "friendly",
  "funky",
  "giddy",
  "giggly",
  "gleeful",
  "goofy",
  "graceful",
  "grinning",
  "hilarious",
  "inquisitive",
  "joyous",
  "jubilant",
  "lively",
  "mirthful",
  "mischievous",
  "optimistic",
  "peppy",
  "perky",
  "playful",
  "quirky",
  "radiant",
  "sassy",
  "silly",
  "spirited",
  "sprightly",
  "twinkly",
  "upbeat",
  "vibrant",
  "witty",
  "zany",
  "zealous",
];
/**
 * Nouns for the name of the flow
 * @constant
 *
 */
export const NOUNS: string[] = [
  "albattani",
  "allen",
  "almeida",
  "archimedes",
  "ardinghelli",
  "aryabhata",
  "austin",
  "babbage",
  "banach",
  "bardeen",
  "bartik",
  "bassi",
  "bell",
  "bhabha",
  "bhaskara",
  "blackwell",
  "bohr",
  "booth",
  "borg",
  "bose",
  "boyd",
  "brahmagupta",
  "brattain",
  "brown",
  "carson",
  "chandrasekhar",
  "colden",
  "cori",
  "cray",
  "curie",
  "darwin",
  "davinci",
  "dijkstra",
  "dubinsky",
  "easley",
  "einstein",
  "elion",
  "engelbart",
  "euclid",
  "euler",
  "fermat",
  "fermi",
  "feynman",
  "franklin",
  "galileo",
  "gates",
  "goldberg",
  "goldstine",
  "goldwasser",
  "golick",
  "goodall",
  "hamilton",
  "hawking",
  "heisenberg",
  "heyrovsky",
  "hodgkin",
  "hoover",
  "hopper",
  "hugle",
  "hypatia",
  "jang",
  "jennings",
  "jepsen",
  "joliot",
  "jones",
  "kalam",
  "kare",
  "keller",
  "khorana",
  "kilby",
  "kirch",
  "knuth",
  "kowalevski",
  "lalande",
  "lamarr",
  "leakey",
  "leavitt",
  "lichterman",
  "liskov",
  "lovelace",
  "lumiere",
  "mahavira",
  "mayer",
  "mccarthy",
  "mcclintock",
  "mclean",
  "mcnulty",
  "meitner",
  "meninsky",
  "mestorf",
  "minsky",
  "mirzakhani",
  "morse",
  "murdock",
  "newton",
  "nobel",
  "noether",
  "northcutt",
  "noyce",
  "panini",
  "pare",
  "pasteur",
  "payne",
  "perlman",
  "pike",
  "poincare",
  "poitras",
  "ptolemy",
  "raman",
  "ramanujan",
  "ride",
  "ritchie",
  "roentgen",
  "rosalind",
  "saha",
  "sammet",
  "shaw",
  "shirley",
  "shockley",
  "sinoussi",
  "snyder",
  "spence",
  "stallman",
  "stonebraker",
  "swanson",
  "swartz",
  "swirles",
  "tesla",
  "thompson",
  "torvalds",
  "turing",
  "varahamihira",
  "visvesvaraya",
  "volhard",
  "wescoff",
  "williams",
  "wilson",
  "wing",
  "wozniak",
  "wright",
  "yalow",
  "yonath",
  "coulomb",
  "degrasse",
  "dewey",
  "edison",
  "eratosthenes",
  "faraday",
  "galton",
  "gauss",
  "herschel",
  "hubble",
  "joule",
  "kaku",
  "kepler",
  "khayyam",
  "lavoisier",
  "maxwell",
  "mendel",
  "mendeleev",
  "ohm",
  "pascal",
  "planck",
  "riemann",
  "schrodinger",
  "sagan",
  "tesla",
  "tyson",
  "volta",
  "watt",
  "weber",
  "wien",
  "zoBell",
  "zuse",
];

export const MAX_MCP_SERVER_NAME_LENGTH = 30;

export const BASE_URL_API = custom.BASE_URL_API || "/api/v1/";

export const BASE_URL_API_V2 = custom.BASE_URL_API_V2 || "/api/v2/";

/**
 * URLs excluded from error retries.
 * @constant
 *
 */
export const URL_EXCLUDED_FROM_ERROR_RETRIES = [
  `${BASE_URL_API}validate/code`,
  `${BASE_URL_API}custom_component`,
  `${BASE_URL_API}validate/prompt`,
  `${BASE_URL_API}/login`,
  `${BASE_URL_API}api_key/store`,
];

export const skipNodeUpdate = [
  "CustomComponent",
  "PromptTemplate",
  "ChatMessagePromptTemplate",
  "SystemMessagePromptTemplate",
  "HumanMessagePromptTemplate",
];

export const CONTROL_INPUT_STATE = {
  password: "",
  cnfPassword: "",
  username: "",
};

export const CONTROL_PATCH_USER_STATE = {
  password: "",
  cnfPassword: "",
  profilePicture: "",
  apikey: "",
};

export const CONTROL_LOGIN_STATE = {
  username: "",
  password: "",
};

export const CONTROL_NEW_USER = {
  username: "",
  password: "",
  is_active: false,
  is_superuser: false,
};

export const tabsCode = [];

export const LANGFLOW_SUPPORTED_TYPES = new Set([
  "str",
  "bool",
  "float",
  "code",
  "prompt",
  "file",
  "int",
  "dict",
  "NestedDict",
  "table",
  "link",
  "slider",
  "tab",
  "sortableList",
  "connect",
  "auth",
  "query",
  "mcp",
  "tools",
]);

export const FLEX_VIEW_TYPES = ["bool"];

export const priorityFields = new Set(["code", "template", "mode"]);

export const INPUT_TYPES = new Set([
  "ChatInput",
  // "TextInput",
  // "KeyPairInput",
  // "JsonInput",
  // "StringListInput",
]);
export const OUTPUT_TYPES = new Set([
  "ChatOutput",
  // "TextOutput",
  // "PDFOutput",
  // "ImageOutput",
  // "CSVOutput",
  // "JsonOutput",
  // "KeyPairOutput",
  // "StringListOutput",
  // "DataOutput",
  // "TableOutput",
]);

export const SUCCESS_BUILD = "Built successfully ✨";

export const PRIORITY_SIDEBAR_ORDER = [
  "saved_components",
  "inputs",
  "outputs",
  "prompts",
  "data",
  "prompt",
  "models",
  "helpers",
  "vectorstores",
  "embeddings",
];

export const BUNDLES_SIDEBAR_FOLDER_NAMES = [
  "notion",
  "Notion",
  "AssemblyAI",
  "assemblyai",
  "LangWatch",
  "langwatch",
  "YouTube",
  "youtube",
  "pinecone",
  "weaviate",
  "qdrant",
  "mongodb",
  "elastic",
  "supabase",
  "milvus",
  "chroma",
  "clickhouse",
  "couchbase",
  "upstash",
  "vectara",
  "cassandra",
  "FAISS",
  "pgvector",
];

export const AUTHORIZED_DUPLICATE_REQUESTS = [
  "/health",
  "/flows",
  "/logout",
  "/refresh",
  "/login",
  "/auto_login",
];

export const BROKEN_EDGES_WARNING =
  "Some connections were removed because they were invalid:";

export const SAVE_DEBOUNCE_TIME = 300;

export const IS_MAC =
  typeof navigator !== "undefined" &&
  navigator.userAgent.toUpperCase().includes("MAC");

export const defaultShortcuts = customDefaultShortcuts;

export const LOCATIONS_TO_RETURN = ["/flow/", "/settings/"];

export const MAX_BATCH_SIZE = 50;

export const MODAL_CLASSES =
  "nopan nodelete nodrag  noflow fixed inset-0 bottom-0 left-0 right-0 top-0 z-50 overflow-auto bg-black/50 backdrop-blur-sm data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0";

export const ALLOWED_IMAGE_INPUT_EXTENSIONS = ["png", "jpg", "jpeg"];

export const componentsToIgnoreUpdate = ["CustomComponent"];

export const FS_ERROR_TEXT =
  "Please ensure your file has one of the following extensions:";
export const SN_ERROR_TEXT = ALLOWED_IMAGE_INPUT_EXTENSIONS.join(", ");

export const ERROR_UPDATING_COMPONENT =
  "An unexpected error occurred while updating the Component. Please try again.";
export const TITLE_ERROR_UPDATING_COMPONENT =
  "Error while updating the Component";

export const EMPTY_INPUT_SEND_MESSAGE = "No input message provided.";

export const EMPTY_OUTPUT_SEND_MESSAGE = "Message empty.";

export const TABS_ORDER = [
  "curl",
  "python api",
  "js api",
  "python code",
  "chat widget html",
];

export const LANGFLOW_ACCESS_TOKEN = "access_token_lf";
export const LANGFLOW_API_TOKEN = "apikey_tkn_lflw";
export const LANGFLOW_AUTO_LOGIN_OPTION = "auto_login_lf";
export const LANGFLOW_REFRESH_TOKEN = "refresh_token_lf";

export const LANGFLOW_ACCESS_TOKEN_EXPIRE_SECONDS = 60 * 60 - 60 * 60 * 0.1;
export const LANGFLOW_ACCESS_TOKEN_EXPIRE_SECONDS_ENV =
  Number(process.env?.ACCESS_TOKEN_EXPIRE_SECONDS ?? 60) -
  Number(process.env?.ACCESS_TOKEN_EXPIRE_SECONDS ?? 60) * 0.1;
export const TEXT_FIELD_TYPES: string[] = ["str", "SecretStr"];
export const NODE_WIDTH = 384;
export const NODE_HEIGHT = NODE_WIDTH * 3;

export const SHORTCUT_KEYS = ["cmd", "ctrl", "mod", "alt", "shift"];

export const SERVER_HEALTH_INTERVAL = 10000;
export const REFETCH_SERVER_HEALTH_INTERVAL = 20000;
export const DRAG_EVENTS_CUSTOM_TYPESS = {
  genericnode: "genericNode",
  notenode: "noteNode",
  "text/plain": "text/plain",
};

export const NOTE_NODE_MIN_WIDTH = 324;
export const NOTE_NODE_MIN_HEIGHT = 324;
export const NOTE_NODE_MAX_HEIGHT = 800;
export const NOTE_NODE_MAX_WIDTH = 1000;

export const COLOR_OPTIONS = {
  amber: "hsl(var(--note-amber))",
  neutral: "hsl(var(--note-neutral))",
  rose: "hsl(var(--note-rose))",
  blue: "hsl(var(--note-blue))",
  lime: "hsl(var(--note-lime))",
  transparent: null,
};

export const maxSizeFilesInBytes = 10 * 1024 * 1024; // 10MB in bytes
export const MAX_TEXT_LENGTH = 99999;

export const SEARCH_TABS = ["All", "Flows", "Components"];
export const PAGINATION_SIZE = 12;
export const PAGINATION_PAGE = 1;

export const STORE_PAGINATION_SIZE = 12;
export const STORE_PAGINATION_PAGE = 1;

export const PAGINATION_ROWS_COUNT = [12, 24, 48, 96];
export const STORE_PAGINATION_ROWS_COUNT = [12, 24, 48, 96];

export const GRADIENT_CLASS =
  "linear-gradient(to right, hsl(var(--background) / 0.3), hsl(var(--background)))";

export const GRADIENT_CLASS_DISABLED =
  "linear-gradient(to right, hsl(var(--muted) / 0.3), hsl(var(--muted)))";

export const ICON_STROKE_WIDTH = 1.5;

export const SAVE_API_KEY_ALERT = "API key saved successfully";
export const POLLING_MESSAGES = {
  ENDPOINT_NOT_AVAILABLE: "Endpoint not available",
  STREAMING_NOT_SUPPORTED: "Streaming not supported",
} as const;

export const BUILD_POLLING_INTERVAL = 25;

export const IS_AUTO_LOGIN =
  !process?.env?.LANGFLOW_AUTO_LOGIN ||
  String(process?.env?.LANGFLOW_AUTO_LOGIN)?.toLowerCase() !== "false";

export const AUTO_LOGIN_RETRY_DELAY = 2000;
export const AUTO_LOGIN_MAX_RETRY_DELAY = 60000;

export const ALL_LANGUAGES = [
  { value: "en-US", name: "English (US)" },
  { value: "en-GB", name: "English (UK)" },
  { value: "it-IT", name: "Italian" },
  { value: "fr-FR", name: "French" },
  { value: "es-ES", name: "Spanish" },
  { value: "de-DE", name: "German" },
  { value: "ja-JP", name: "Japanese" },
  { value: "pt-BR", name: "Portuguese (Brazil)" },
  { value: "zh-CN", name: "Chinese (Simplified)" },
  { value: "ru-RU", name: "Russian" },
  { value: "ar-SA", name: "Arabic" },
  { value: "hi-IN", name: "Hindi" },
];

export const DEBOUNCE_FIELD_LIST = [
  "SecretStrInput",
  "MessageTextInput",
  "TextInput",
  "MultilineInput",
  "SecretStrInput",
  "IntInput",
  "FloatInput",
  "SliderInput",
];

export const OPENAI_VOICES = [
  { name: "alloy", value: "alloy" },
  { name: "ash", value: "ash" },
  { name: "ballad", value: "ballad" },
  { name: "coral", value: "coral" },
  { name: "echo", value: "echo" },
  { name: "sage", value: "sage" },
  { name: "shimmer", value: "shimmer" },
  { name: "verse", value: "verse" },
];

export const DEFAULT_POLLING_INTERVAL = 5000;
export const DEFAULT_TIMEOUT = 30000;
export const DEFAULT_FILE_PICKER_TIMEOUT = 60000;
export const DISCORD_URL = "https://discord.com/invite/EqksyE2EX9";
export const GITHUB_URL = "https://github.com/langflow-ai/langflow";
export const TWITTER_URL = "https://x.com/langflow_ai";
export const DOCS_URL = "https://docs.langflow.org";
export const DATASTAX_DOCS_URL =
  "https://docs.datastax.com/en/langflow/index.html";
export const DESKTOP_URL = "https://www.langflow.org/desktop";
export const BUG_REPORT_URL = "https://github.com/langflow-ai/langflow/issues";

export const UUID_PARSING_ERROR = "uuid_parsing";
