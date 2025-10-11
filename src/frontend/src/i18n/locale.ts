import { ENABLE_KNOWLEDGE_BASES } from '@/customization/feature-flags';
import { useMemo } from 'react';
import { useTranslation } from 'react-i18next';

export const useSidebarCategories = () => {
  const { t } = useTranslation();

  return useMemo(
    () => [
      {
        display_name: t('flow.sidebar.components.savedComponents'),
        name: 'saved_components',
        icon: 'GradientSave',
      },
      {
        display_name: t('flow.sidebar.components.inputOutput'),
        name: 'input_output',
        icon: 'Cable',
      },
      {
        display_name: t('flow.sidebar.components.agents'),
        name: 'agents',
        icon: 'Bot',
      },
      {
        display_name: t('flow.sidebar.components.models'),
        name: 'models',
        icon: 'BrainCog',
      },
      {
        display_name: t('flow.sidebar.components.data'),
        name: 'data',
        icon: 'Database',
      },
      ...(ENABLE_KNOWLEDGE_BASES
        ? [
            {
              display_name: t('flow.sidebar.components.knowledgeBases'),
              name: 'knowledge_bases',
              icon: 'Library',
            },
          ]
        : []),
      {
        display_name: t('flow.sidebar.components.vectorstores'),
        name: 'vectorstores',
        icon: 'Layers',
      },
      {
        display_name: t('flow.sidebar.components.processing'),
        name: 'processing',
        icon: 'ListFilter',
      },
      {
        display_name: t('flow.sidebar.components.logic'),
        name: 'logic',
        icon: 'ArrowRightLeft',
      },
      {
        display_name: t('flow.sidebar.components.helpers'),
        name: 'helpers',
        icon: 'Wand2',
      },
      {
        display_name: t('flow.sidebar.components.inputs'),
        name: 'inputs',
        icon: 'Download',
      },
      {
        display_name: t('flow.sidebar.components.outputs'),
        name: 'outputs',
        icon: 'Upload',
      },
      {
        display_name: t('flow.sidebar.components.prompts'),
        name: 'prompts',
        icon: 'braces',
      },
      {
        display_name: t('flow.sidebar.components.chains'),
        name: 'chains',
        icon: 'Link',
      },
      {
        display_name: t('flow.sidebar.components.documentloaders'),
        name: 'documentloaders',
        icon: 'Paperclip',
      },
      {
        display_name: t('flow.sidebar.components.linkExtractors'),
        name: 'link_extractors',
        icon: 'Link2',
      },
      {
        display_name: t('flow.sidebar.components.outputParsers'),
        name: 'output_parsers',
        icon: 'Compass',
      },
      {
        display_name: t('flow.sidebar.components.prototypes'),
        name: 'prototypes',
        icon: 'FlaskConical',
      },
      {
        display_name: t('flow.sidebar.components.retrievers'),
        name: 'retrievers',
        icon: 'FileSearch',
      },
      {
        display_name: t('flow.sidebar.components.textsplitters'),
        name: 'textsplitters',
        icon: 'Scissors',
      },
      {
        display_name: t('flow.sidebar.components.toolkits'),
        name: 'toolkits',
        icon: 'Package2',
      },
      {
        display_name: t('flow.sidebar.components.tools'),
        name: 'tools',
        icon: 'Hammer',
      },
    ],
    []
  );
};

export const useSidebarBundles = () => {
  const { t } = useTranslation();

  return useMemo(
    () => [
      {
        display_name: t('flow.sidebar.bundles.aimlApi'),
        name: 'aiml',
        icon: 'AIML',
      },
      {
        display_name: t('flow.sidebar.bundles.agentql'),
        name: 'agentql',
        icon: 'AgentQL',
      },
      {
        display_name: t('flow.sidebar.bundles.languageModels'),
        name: 'languagemodels',
        icon: 'BrainCircuit',
      },
      {
        display_name: t('flow.sidebar.bundles.embeddings'),
        name: 'embeddings',
        icon: 'Binary',
      },
      {
        display_name: t('flow.sidebar.bundles.memories'),
        name: 'memories',
        icon: 'Cpu',
      },
      {
        display_name: t('flow.sidebar.bundles.amazon'),
        name: 'amazon',
        icon: 'Amazon',
      },
      {
        display_name: t('flow.sidebar.bundles.anthropic'),
        name: 'anthropic',
        icon: 'Anthropic',
      },
      {
        display_name: t('flow.sidebar.bundles.apify'),
        name: 'apify',
        icon: 'Apify',
      },
      {
        display_name: t('flow.sidebar.bundles.arxiv'),
        name: 'arxiv',
        icon: 'arXiv',
      },
      {
        display_name: t('flow.sidebar.bundles.assemblyai'),
        name: 'assemblyai',
        icon: 'AssemblyAI',
      },
      {
        display_name: t('flow.sidebar.bundles.azure'),
        name: 'azure',
        icon: 'Azure',
      },
      {
        display_name: t('flow.sidebar.bundles.baidu'),
        name: 'baidu',
        icon: 'BaiduQianfan',
      },
      {
        display_name: t('flow.sidebar.bundles.bing'),
        name: 'bing',
        icon: 'Bing',
      },
      {
        display_name: t('flow.sidebar.bundles.cassandra'),
        name: 'cassandra',
        icon: 'Cassandra',
      },
      {
        display_name: t('flow.sidebar.bundles.chroma'),
        name: 'chroma',
        icon: 'Chroma',
      },
      {
        display_name: t('flow.sidebar.bundles.clickhouse'),
        name: 'clickhouse',
        icon: 'Clickhouse',
      },
      {
        display_name: t('flow.sidebar.bundles.cleanlab'),
        name: 'cleanlab',
        icon: 'Cleanlab',
      },
      {
        display_name: t('flow.sidebar.bundles.cloudflare'),
        name: 'cloudflare',
        icon: 'Cloudflare',
      },
      {
        display_name: t('flow.sidebar.bundles.cohere'),
        name: 'cohere',
        icon: 'Cohere',
      },
      {
        display_name: t('flow.sidebar.bundles.composio'),
        name: 'composio',
        icon: 'Composio',
      },
      {
        display_name: t('flow.sidebar.bundles.confluence'),
        name: 'confluence',
        icon: 'Confluence',
      },
      {
        display_name: t('flow.sidebar.bundles.couchbase'),
        name: 'couchbase',
        icon: 'Couchbase',
      },
      {
        display_name: t('flow.sidebar.bundles.crewai'),
        name: 'crewai',
        icon: 'CrewAI',
      },
      {
        display_name: t('flow.sidebar.bundles.datastax'),
        name: 'datastax',
        icon: 'AstraDB',
      },
      {
        display_name: t('flow.sidebar.bundles.deepseek'),
        name: 'deepseek',
        icon: 'DeepSeek',
      },
      {
        display_name: t('flow.sidebar.bundles.docling'),
        name: 'docling',
        icon: 'Docling',
      },
      {
        display_name: t('flow.sidebar.bundles.duckduckgo'),
        name: 'duckduckgo',
        icon: 'DuckDuckGo',
      },
      {
        display_name: t('flow.sidebar.bundles.elastic'),
        name: 'elastic',
        icon: 'ElasticsearchStore',
      },
      { display_name: t('flow.sidebar.bundles.exa'), name: 'exa', icon: 'Exa' },
      {
        display_name: t('flow.sidebar.bundles.faiss'),
        name: 'FAISS',
        icon: 'FAISS',
      },
      {
        display_name: t('flow.sidebar.bundles.firecrawl'),
        name: 'firecrawl',
        icon: 'FirecrawlCrawlApi',
      },
      {
        display_name: t('flow.sidebar.bundles.git'),
        name: 'git',
        icon: 'GitLoader',
      },
      {
        display_name: t('flow.sidebar.bundles.glean'),
        name: 'glean',
        icon: 'Glean',
      },
      {
        display_name: t('flow.sidebar.bundles.gmail'),
        name: 'gmail',
        icon: 'Gmail',
      },
      {
        display_name: t('flow.sidebar.bundles.google'),
        name: 'google',
        icon: 'Google',
      },
      {
        display_name: t('flow.sidebar.bundles.groq'),
        name: 'groq',
        icon: 'Groq',
      },
      {
        display_name: t('flow.sidebar.bundles.homeAssistant'),
        name: 'homeassistant',
        icon: 'HomeAssistant',
      },
      {
        display_name: t('flow.sidebar.bundles.huggingface'),
        name: 'huggingface',
        icon: 'HuggingFace',
      },
      {
        display_name: t('flow.sidebar.bundles.ibm'),
        name: 'ibm',
        icon: 'WatsonxAI',
      },
      {
        display_name: t('flow.sidebar.bundles.icosacomputing'),
        name: 'icosacomputing',
        icon: 'Icosa',
      },
      {
        display_name: t('flow.sidebar.bundles.jigsawstack'),
        name: 'jigsawstack',
        icon: 'JigsawStack',
      },
      {
        display_name: t('flow.sidebar.bundles.langchain'),
        name: 'langchain_utilities',
        icon: 'LangChain',
      },
      {
        display_name: t('flow.sidebar.bundles.langwatch'),
        name: 'langwatch',
        icon: 'Langwatch',
      },
      {
        display_name: t('flow.sidebar.bundles.lmstudio'),
        name: 'lmstudio',
        icon: 'LMStudio',
      },
      {
        display_name: t('flow.sidebar.bundles.maritalk'),
        name: 'maritalk',
        icon: 'Maritalk',
      },
      {
        display_name: t('flow.sidebar.bundles.mem0'),
        name: 'mem0',
        icon: 'Mem0',
      },
      {
        display_name: t('flow.sidebar.bundles.memories'),
        name: 'memories',
        icon: 'Cpu',
      },
      {
        display_name: t('flow.sidebar.bundles.milvus'),
        name: 'milvus',
        icon: 'Milvus',
      },
      {
        display_name: t('flow.sidebar.bundles.mistral'),
        name: 'mistral',
        icon: 'MistralAI',
      },
      {
        display_name: t('flow.sidebar.bundles.mongodb'),
        name: 'mongodb',
        icon: 'MongoDB',
      },
      {
        display_name: t('flow.sidebar.bundles.needle'),
        name: 'needle',
        icon: 'Needle',
      },
      {
        display_name: t('flow.sidebar.bundles.notdiamond'),
        name: 'notdiamond',
        icon: 'NotDiamond',
      },
      {
        display_name: t('flow.sidebar.bundles.notion'),
        name: 'Notion',
        icon: 'Notion',
      },
      {
        display_name: t('flow.sidebar.bundles.novita'),
        name: 'novita',
        icon: 'Novita',
      },
      {
        display_name: t('flow.sidebar.bundles.nvidia'),
        name: 'nvidia',
        icon: 'NVIDIA',
      },
      {
        display_name: t('flow.sidebar.bundles.olivya'),
        name: 'olivya',
        icon: 'Olivya',
      },
      {
        display_name: t('flow.sidebar.bundles.ollama'),
        name: 'ollama',
        icon: 'Ollama',
      },
      {
        display_name: t('flow.sidebar.bundles.openai'),
        name: 'openai',
        icon: 'OpenAI',
      },
      {
        display_name: t('flow.sidebar.bundles.openrouter'),
        name: 'openrouter',
        icon: 'OpenRouter',
      },
      {
        display_name: t('flow.sidebar.bundles.perplexity'),
        name: 'perplexity',
        icon: 'Perplexity',
      },
      {
        display_name: t('flow.sidebar.bundles.pgvector'),
        name: 'pgvector',
        icon: 'cpu',
      },
      {
        display_name: t('flow.sidebar.bundles.pinecone'),
        name: 'pinecone',
        icon: 'Pinecone',
      },
      {
        display_name: t('flow.sidebar.bundles.qdrant'),
        name: 'qdrant',
        icon: 'Qdrant',
      },
      {
        display_name: t('flow.sidebar.bundles.redis'),
        name: 'redis',
        icon: 'Redis',
      },
      {
        display_name: t('flow.sidebar.bundles.sambanova'),
        name: 'sambanova',
        icon: 'SambaNova',
      },
      {
        display_name: t('flow.sidebar.bundles.scrapegraph'),
        name: 'scrapegraph',
        icon: 'ScrapeGraph',
      },
      {
        display_name: t('flow.sidebar.bundles.searchapi'),
        name: 'searchapi',
        icon: 'SearchAPI',
      },
      {
        display_name: t('flow.sidebar.bundles.serpapi'),
        name: 'serpapi',
        icon: 'SerpSearch',
      },
      {
        display_name: t('flow.sidebar.bundles.serper'),
        name: 'serper',
        icon: 'Serper',
      },
      {
        display_name: t('flow.sidebar.bundles.supabase'),
        name: 'supabase',
        icon: 'Supabase',
      },
      {
        display_name: t('flow.sidebar.bundles.tavily'),
        name: 'tavily',
        icon: 'TavilyIcon',
      },
      {
        display_name: t('flow.sidebar.bundles.twelvelabs'),
        name: 'twelvelabs',
        icon: 'TwelveLabs',
      },
      {
        display_name: t('flow.sidebar.bundles.unstructured'),
        name: 'unstructured',
        icon: 'Unstructured',
      },
      {
        display_name: t('flow.sidebar.bundles.upstash'),
        name: 'upstash',
        icon: 'Upstash',
      },
      {
        display_name: t('flow.sidebar.bundles.vectara'),
        name: 'vectara',
        icon: 'Vectara',
      },
      {
        display_name: t('flow.sidebar.bundles.vectorStores'),
        name: 'vectorstores',
        icon: 'Layers',
      },
      {
        display_name: t('flow.sidebar.bundles.weaviate'),
        name: 'weaviate',
        icon: 'Weaviate',
      },
      {
        display_name: t('flow.sidebar.bundles.vertexai'),
        name: 'vertexai',
        icon: 'VertexAI',
      },
      {
        display_name: t('flow.sidebar.bundles.wikipedia'),
        name: 'wikipedia',
        icon: 'Wikipedia',
      },
      {
        display_name: t('flow.sidebar.bundles.wolframalpha'),
        name: 'wolframalpha',
        icon: 'WolframAlphaAPI',
      },
      { display_name: t('flow.sidebar.bundles.xai'), name: 'xai', icon: 'xAI' },
      {
        display_name: t('flow.sidebar.bundles.yahooFinance'),
        name: 'yahoosearch',
        icon: 'trending-up',
      },
      {
        display_name: t('flow.sidebar.bundles.youtube'),
        name: 'youtube',
        icon: 'YouTube',
      },
      {
        display_name: t('flow.sidebar.bundles.zep'),
        name: 'zep',
        icon: 'ZepMemory',
      },
    ],
    []
  );
};

export const useShortcutsLocale = () => {
  const { t } = useTranslation();

  return useMemo(
    () => [
      {
        display_name: t('shortcuts.controls'),
        name: 'Advanced Settings',
        shortcut: 'mod+shift+a',
      },
      {
        display_name: t('shortcuts.searchComponentsSidebar'),
        name: 'Search Components Sidebar',
        shortcut: '/',
      },
      {
        display_name: t('shortcuts.minimize'),
        name: 'Minimize',
        shortcut: 'mod+.',
      },
      {
        display_name: t('shortcuts.code'),
        name: 'Code',
        shortcut: 'space',
      },
      {
        display_name: t('shortcuts.copy'),
        name: 'Copy',
        shortcut: 'mod+c',
      },
      {
        display_name: t('shortcuts.duplicate'),
        name: 'Duplicate',
        shortcut: 'mod+d',
      },
      {
        display_name: t('shortcuts.componentShare'),
        name: 'Component Share',
        shortcut: 'mod+shift+s',
      },
      {
        display_name: t('shortcuts.docs'),
        name: 'Docs',
        shortcut: 'mod+shift+d',
      },
      {
        display_name: t('shortcuts.changesSave'),
        name: 'Changes Save',
        shortcut: 'mod+s',
      },
      {
        display_name: t('shortcuts.saveComponent'),
        name: 'Save Component',
        shortcut: 'mod+alt+s',
      },
      {
        display_name: t('shortcuts.delete'),
        name: 'Delete',
        shortcut: 'backspace',
      },
      {
        display_name: t('shortcuts.openPlayground'),
        name: 'Open Playground',
        shortcut: 'mod+k',
      },
      {
        display_name: t('shortcuts.undo'),
        name: 'Undo',
        shortcut: 'mod+z',
      },
      {
        display_name: t('shortcuts.redo'),
        name: 'Redo',
        shortcut: 'mod+y',
      },
      {
        display_name: t('shortcuts.redoAlt'),
        name: 'Redo Alt',
        shortcut: 'mod+shift+z',
      },
      {
        display_name: t('shortcuts.group'),
        name: 'Group',
        shortcut: 'mod+g',
      },
      {
        display_name: t('shortcuts.cut'),
        name: 'Cut',
        shortcut: 'mod+x',
      },
      {
        display_name: t('shortcuts.paste'),
        name: 'Paste',
        shortcut: 'mod+v',
      },
      {
        display_name: t('shortcuts.api'),
        name: 'API',
        shortcut: 'r',
      },
      {
        display_name: t('shortcuts.download'),
        name: 'Download',
        shortcut: 'mod+j',
      },
      {
        display_name: t('shortcuts.update'),
        name: 'Update',
        shortcut: 'mod+u',
      },
      {
        display_name: t('shortcuts.freezePath'),
        name: 'Freeze Path',
        shortcut: 'mod+shift+f',
      },
      {
        display_name: t('shortcuts.flowShare'),
        name: 'Flow Share',
        shortcut: 'mod+shift+b',
      },
      {
        display_name: t('shortcuts.play'),
        name: 'Play',
        shortcut: 'p',
      },
      {
        display_name: t('shortcuts.outputInspection'),
        name: 'Output Inspection',
        shortcut: 'o',
      },
      {
        display_name: t('shortcuts.toolMode'),
        name: 'Tool Mode',
        shortcut: 'mod+shift+m',
      },
      {
        display_name: t('shortcuts.toggleSidebar'),
        name: 'Toggle Sidebar',
        shortcut: 'mod+b',
      },
    ],
    [t]
  );
};


export const useMessageLocale = () => {
  const { t } = useTranslation();

  return useMemo(() => {
    return {
      "DEFAULT_TABLE_ALERT_MSG": t("messages.alertMessage"),
      "DEFAULT_TABLE_ALERT_TITLE": t("messages.noData"),
      "NO_COLUMN_DEFINITION_ALERT_TITLE": t("messages.noColumnDefinitionTitle"),
      "NO_COLUMN_DEFINITION_ALERT_DESCRIPTION": t("messages.noColumnDefinitionDescription"),
      "FS_ERROR_TEXT": t("messages.fsErrorText"),
      "ERROR_UPDATING_COMPONENT": t("messages.errorUpdatingComponent"),
      "TITLE_ERROR_UPDATING_COMPONENT": t("messages.titleErrorUpdatingComponent"),
      "EMPTY_INPUT_SEND_MESSAGE": t("messages.emptyInputSend"),
      "EMPTY_OUTPUT_SEND_MESSAGE": t("messages.emptyOutputSend"),
      "CSV_VIEW_ERROR_TITLE": t("messages.csvViewErrorTitle"),
      "CSV_NO_DATA_ERROR": t("messages.csvNoDataError"),
      "PDF_VIEW_CONSTANT": t("messages.pdfViewConstant"),
      "CSV_ERROR": t("messages.csvError"),
      "PDF_LOAD_ERROR_TITLE": t("messages.pdfLoadErrorTitle"),
      "PDF_CHECK_FLOW": t("messages.pdfCheckFlow"),
      "PDF_ERROR_TITLE": t("messages.pdfErrorTitle"),
      "PDF_LOAD_ERROR": t("messages.pdfLoadError"),
      "IMG_VIEW_CONSTANT": t("messages.imgViewConstant"),
      "IMG_VIEW_ERROR_MSG": t("messages.imgViewErrorMsg"),
      "IMG_VIEW_ERROR_TITLE": t("messages.imgViewErrorTitle"),
      "FLOW_BUILT_FAILED": t("messages.flowBuildFailed"),
      "FLOW_BUILT_SUCCESSFULLY": t("messages.flowBuiltSuccessfully"),
    }
  },[])
}

export const useFormLocale = () => {
  const { t } = useTranslation();

  return useMemo(() => {
    return {
      "DEFAULT_PLACEHOLDER": t('forms.defaultPlaceholder'),
      "RECEIVING_INPUT_VALUE": t("forformsm.receivingInputValue"),
      "SELECT_AN_OPTION": t("forms.selectOptions"),
      "DEFAULT_TOOLSET_PLACEHOLDER": t('forms.defaultToolsetPlaceholder'),
      "EDIT_TEXT_PLACEHOLDER": t("forms.editTextPlaceholder"),
      "EDIT_TEXT_MODAL_TITLE": t("forms.editTextModalTitle"),
      "TEXT_DIALOG_TITLE": t("forms.textDialogTitle")
    }
  },[])
}