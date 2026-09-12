/* o89 loader: stitch storyboard parts then eval as one IIFE */
(function(){
  var PARTS = ["/static/storyboard.o89.1.part.js?v=o89vid", "/static/storyboard.o89.2.part.js?v=o89vid", "/static/storyboard.o89.3.part.js?v=o89vid", "/static/storyboard.o89.4.part.js?v=o89vid", "/static/storyboard.o89.5.part.js?v=o89vid"];
  var acc = "";
  (async function(){
    for (var i=0;i<PARTS.length;i++){
      var r = await fetch(PARTS[i], {cache:"no-store"});
      if (!r.ok) throw new Error("o89 part "+PARTS[i]+" "+r.status);
      acc += await r.text();
    }
    (0, eval)(acc);
  })().catch(function(e){ console.error(e); });
})();
