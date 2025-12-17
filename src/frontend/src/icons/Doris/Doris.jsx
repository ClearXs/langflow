const SvgDoris = (props) => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    width="1em"
    height="1em"
    viewBox="0 0 32 32"
    {...props}
  >
    <g fill={props.className?.includes("dark") ? "#ffffff" : "#4E8AD9"}>
      <rect x="6" y="8" width="4" height="16" />
      <rect x="12" y="6" width="4" height="20" />
      <rect x="18" y="10" width="4" height="12" />
      <rect x="24" y="12" width="2" height="8" />
    </g>
  </svg>
);
export default SvgDoris;
