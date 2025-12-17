const SvgHive = (props) => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    width="1em"
    height="1em"
    viewBox="0 0 32 32"
    {...props}
  >
    <path
      fill={props.className?.includes("dark") ? "#ffffff" : "#FDDB3E"}
      d="M16 4l-8 4.619v9.238L16 22.476l8-4.619V8.619zm0 2.285l5.714 3.301v6.6L16 19.488l-5.714-3.302v-6.6zM12 10v2h2v-2zm4 0v2h2v-2zm-6 3v2h2v-2zm4 0v2h2v-2zm4 0v2h2v-2zm-6 3v2h2v-2zm4 0v2h2v-2z"
    />
  </svg>
);
export default SvgHive;
