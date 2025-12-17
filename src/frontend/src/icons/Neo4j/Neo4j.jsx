const SvgNeo4j = (props) => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    width="1em"
    height="1em"
    viewBox="0 0 32 32"
    {...props}
  >
    <g fill={props.className?.includes("dark") ? "#ffffff" : "#008CC1"}>
      <circle cx="16" cy="16" r="3" />
      <circle cx="8" cy="8" r="2.5" />
      <circle cx="24" cy="8" r="2.5" />
      <circle cx="8" cy="24" r="2.5" />
      <circle cx="24" cy="24" r="2.5" />
    </g>
    <g
      fill="none"
      stroke={props.className?.includes("dark") ? "#ffffff" : "#008CC1"}
      strokeWidth="1.5"
    >
      <line x1="16" y1="13" x2="10" y2="9.5" />
      <line x1="16" y1="13" x2="22" y2="9.5" />
      <line x1="16" y1="19" x2="10" y2="22.5" />
      <line x1="16" y1="19" x2="22" y2="22.5" />
    </g>
  </svg>
);
export default SvgNeo4j;
