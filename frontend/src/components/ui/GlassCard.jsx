function GlassCard({

  children,

  className = "",

  gradient = "",

  hover = true,

  onClick,

}) {

  const gradientClass = gradient
    ? `gradient-card-${gradient}`
    : "";


  return (

    <div
      onClick={onClick}
      className={`rounded-xl p-6 ${
        hover ? "glass-card" : "glass-panel"
      } ${gradientClass} ${className} ${
        onClick ? "cursor-pointer" : ""
      }`}
    >

      {children}

    </div>

  );

}

export default GlassCard;
