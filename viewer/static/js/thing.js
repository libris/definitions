$(function () {

  // Copy everything
  var createDuplicates = function () {
    $('.link-item').each(function() {
      var $subject = $(this);
      $subject.addClass('link-item-original');
      var $copy = $subject.clone();
      var bounding = $subject[0].getBoundingClientRect();
      $copy.addClass('link-item-copy').appendTo($subject.parent());
      $copy.removeClass('link-item-original');
      $copy.css('top', $subject.position().top).css('left', $subject.position().left);
    });
  }

  var expand = function (elem) {
    elem.addClass('to-be-active');
    setTimeout(function() {
      if(elem.hasClass('to-be-active')) {
        
        elem.addClass('active');
        elem.css('width', 500);
        
        if(!elem.hasClass('adjusted-top')) {
          var $parent = elem.closest('li');
          if ($parent.length == 0) {
            $parent = elem.closest('dd');
          }
          var $rootHeading = $parent.find('.link-item-original .panel-title');
          var $elemHeading = $parent.find('.link-item-copy .panel-title');
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
