$(function () {

  
  var createDuplicates = function () {
    // Copies every chip so that we can use absolute positioning on
    // the expanded chips without breaking the layout.
    $('.link-item').each(function() {
      var $subject = $(this);
      var $copy = $subject.clone();
      $subject.addClass('link-item-original');
      $copy.addClass('link-item-copy').appendTo($subject.parent());
      $copy.css('top', $subject.position().top).css('left', $subject.position().left);
    });
  }

  var expand = function (elem) {
    elem.addClass('to-be-active');
    var resource = elem.attr('resource');
    setTimeout(function() {
      if(elem.hasClass('to-be-active')) {
        elem.addClass('active');
        elem.css('width', 500);
        if(!elem.hasClass('adjusted-top')) {
          // Adjust position so that the chip "grows" around the prefLabel
          var $parent = elem.closest('li');
          if ($parent.length == 0) {
            $parent = elem.closest('dd');
          }
          var $rootHeading = $parent.find('.link-item-original[resource="'+resource+'"] .panel-title');
          var $elemHeading = $parent.find('.link-item-copy[resource="'+resource+'"] .panel-title');
          var diffY = $elemHeading.offset().top - $rootHeading.offset().top;
          elem.css('margin-top', -diffY);
          elem.addClass('adjusted-top');
        }
      }
    }, 500);
    
  };
  var collapse = function (elem) {
    elem.removeClass('to-be-active');
    elem.removeClass('active');
    elem.css('margin-top', '');
    elem.removeClass('adjusted-top');
    
    elem.css('width', '').css('height', '');
  };

  $(document).ready(function () {
    setTimeout(function() {
      // Small delay to let the chips stack correctly in their lists
      // before we copy every position.
      createDuplicates();
      
      $('.link-item-copy').hover(function() {
        expand($(this));
      }, function() {
        collapse($(this));
      }).focusin(function() {
        expand($(this));
      }).focusout(function() {
        collapse($(this));
      });
      
    }, 10);
  });

});
