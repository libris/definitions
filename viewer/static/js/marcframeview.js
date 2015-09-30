$(function () {
  
  $(document).on('click', ".menu-col .tab-content a, .marcframetable a[href^='#']", function(e) {
    e.preventDefault();
    var ref = $(this).attr('href');
    setActive(ref);
  });
  
  function setActive(ref) {
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
