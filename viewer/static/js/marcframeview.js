$(function () {
  
  $(document).on('click', ".menu-col .tab-content a, .marcframetable a[href^='#']", function(e) {
    e.preventDefault();
    var ref = $(this).attr('href');
    setActive(ref);
  });
  
  function setActive(ref) {
    
    // Log
    var logRef = ref.split('#')[1];
    var layoutRef = $('body').attr('id');
    if (typeof(_paq) !== 'undefined') _paq.push(['trackEvent', layoutRef, 'Menu click', logRef]);
    
    var itemOrg = ref;
    if(ref.indexOf(':') != -1) {
      var parts = ref.split(':');
      itemOrg = ref;
      ref = parts.join('\\:');
    }
    window.location.hash = itemOrg;
    $('body').scrollTop($(ref).offset().top - 50);
  };
  
  $(document).ready(function () {
    // Target Navigation
    if(window.location.hash.length > 0) {
      setTimeout(function () {
        setActive(window.location.hash);
      }, 250);
    }
  })
  

});
