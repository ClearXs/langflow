import {
  IconBrandDiscord,
  IconBrandGithub,
  IconBrandLinkedin,
  IconBrandTwitter,
} from "@tabler/icons-react";
import { Link } from "react-router-dom";
import { Logo } from "@/components/Logo";

export function FooterNew() {
  const pages = [
    {
      title: "Pricing",
      to: "/pricing",
    },
    {
      title: "Docs",
      to: "/docs",
    },
    {
      title: "Contact Us",
      to: "/contact",
    },
  ];

  const socials = [
    {
      title: "Twitter",
      href: "https://x.com/langflow",
      icon: IconBrandTwitter,
    },
    {
      title: "LinkedIn",
      href: "https://www.linkedin.com/company/langflow",
      icon: IconBrandLinkedin,
    },
    {
      title: "GitHub",
      href: "https://github.com/langflow-ai/langflow",
      icon: IconBrandGithub,
    },
    {
      title: "Discord",
      href: "https://discord.gg/langflow",
      icon: IconBrandDiscord,
    },
  ];
  const legals = [
    {
      title: "Privacy Policy",
      to: "/privacy",
    },
    {
      title: "Terms of Service",
      to: "/terms",
    },
  ];

  const signups = [
    {
      title: "Sign In",
      to: "/login",
    },
  ];
  return (
    <div className="border-t border-neutral-100 dark:border-white/[0.1] px-8 py-20 bg-white dark:bg-neutral-950 w-full relative overflow-hidden">
      <div className="max-w-7xl mx-auto text-sm text-neutral-500 flex sm:flex-row flex-col justify-between items-start  md:px-8">
        <div>
          <div className="mr-0 md:mr-4  md:flex mb-4">
            <Logo className="h-6 w-6 rounded-md mr-2" />
            <span className="dark:text-white/90 text-gray-800 text-lg font-bold">
              Langflow
            </span>
          </div>

          <div className="mt-2 ml-2">
            &copy; Langflow 2025. All rights reserved.
          </div>
        </div>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-10 items-start mt-10 sm:mt-0 md:mt-0">
          <div className="flex justify-center space-y-4 flex-col w-full">
            <p className="transition-colors hover:text-text-neutral-800 text-neutral-600 dark:text-neutral-300 font-bold">
              Pages
            </p>
            <ul className="transition-colors hover:text-text-neutral-800 text-neutral-600 dark:text-neutral-300 list-none space-y-4">
              {pages.map((page, idx) => (
                <li key={"pages" + idx} className="list-none">
                  <Link
                    className="transition-colors hover:text-text-neutral-800 "
                    to={page.to}
                  >
                    {page.title}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          <div className="flex justify-center space-y-4 flex-col">
            <p className="transition-colors hover:text-text-neutral-800 text-neutral-600 dark:text-neutral-300 font-bold">
              Socials
            </p>
            <ul className="transition-colors hover:text-text-neutral-800 text-neutral-600 dark:text-neutral-300 list-none space-y-4">
              {socials.map((social, idx) => {
                const Icon = social.icon;
                return (
                  <li key={"social" + idx} className="list-none">
                    <a
                      className="transition-colors hover:text-text-neutral-800 flex items-center gap-2"
                      href={social.href}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      <Icon className="h-5 w-5" />
                      {social.title}
                    </a>
                  </li>
                );
              })}
            </ul>
          </div>

          <div className="flex justify-center space-y-4 flex-col">
            <p className="transition-colors hover:text-text-neutral-800 text-neutral-600 dark:text-neutral-300 font-bold">
              Legal
            </p>
            <ul className="transition-colors hover:text-text-neutral-800 text-neutral-600 dark:text-neutral-300 list-none space-y-4">
              {legals.map((legal, idx) => (
                <li key={"legal" + idx} className="list-none">
                  <Link
                    className="transition-colors hover:text-text-neutral-800 "
                    to={legal.to}
                  >
                    {legal.title}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
          <div className="flex justify-center space-y-4 flex-col">
            <p className="transition-colors hover:text-text-neutral-800 text-neutral-600 dark:text-neutral-300 font-bold">
              Register
            </p>
            <ul className="transition-colors hover:text-text-neutral-800 text-neutral-600 dark:text-neutral-300 list-none space-y-4">
              {signups.map((auth, idx) => (
                <li key={"auth" + idx} className="list-none">
                  <Link
                    className="transition-colors hover:text-text-neutral-800 "
                    to={auth.to}
                  >
                    {auth.title}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
      <p className="text-center mt-20 text-5xl md:text-9xl lg:text-[12rem] xl:text-[13rem] font-bold bg-clip-text text-transparent bg-gradient-to-b from-neutral-50 dark:from-neutral-950 to-neutral-200 dark:to-neutral-800 inset-x-0">
        Langflow
      </p>
    </div>
  );
}
