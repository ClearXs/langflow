import { FaDiscord, FaGithub, FaLanguage } from 'react-icons/fa';
import ShadTooltip from '@/components/common/shadTooltipComponent';
import { DISCORD_URL, GITHUB_URL } from '@/constants/constants';
import { useDarkStore } from '@/stores/darkStore';
import { cn, formatNumber } from '@/utils/utils';
import AlertDropdown from '@/alerts/alertDropDown';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import { Select } from '@/components/ui/select';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { useI18nStore } from '@/stores/i18nStore';

export const LangflowCounts = () => {
  const stars: number | undefined = useDarkStore((state) => state.stars);
  const discordCount: number = useDarkStore((state) => state.discordCount);

  const {lang, setLanguage} = useI18nStore()

  return (
    <div className='flex items-center gap-3'>
      <DropdownMenu>
        <DropdownMenuTrigger>
          <ShadTooltip side='bottom' styleClasses='z-10'>
            <div className='hit-area-hover flex items-center gap-2 rounded-md p-1 text-muted-foreground'>
              <FaLanguage className='h-6 w-6' />
            </div>
          </ShadTooltip>
        </DropdownMenuTrigger>
        <DropdownMenuContent>
          <DropdownMenuItem className={lang == 'en' ? cn('bg-[hsl(var(--accent))]') : undefined} onClick={() => {
            if (lang != 'en') {
              setLanguage('en')
            }
          }}>English</DropdownMenuItem>
          <DropdownMenuItem className={lang == 'zh' ? cn('bg-[hsl(var(--accent))]') : undefined} onClick={() => {
            if (lang != 'zh') {
              setLanguage('zh')
            }
          }}>中文</DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      {/* <ShadTooltip
        content="Go to GitHub repo"
        side="bottom"
        styleClasses="z-10"
      >
        <div className="hit-area-hover flex items-center gap-2 rounded-md p-1 text-muted-foreground">
          <FaGithub className="h-4 w-4" />
          <span className="text-xs font-semibold">{formatNumber(stars)}</span>
        </div>
      </ShadTooltip>

      <ShadTooltip
        content="Go to Discord server"
        side="bottom"
        styleClasses="z-10"
      >
        <div
          onClick={() => window.open(DISCORD_URL, "_blank")}
          className="hit-area-hover flex items-center gap-2 rounded-md p-1 text-muted-foreground"
        >
          <FaDiscord className="h-4 w-4" />
          <span className="text-xs font-semibold">
            {formatNumber(discordCount)}
          </span>
        </div>
      </ShadTooltip> */}
    </div>
  );
};

export default LangflowCounts;
