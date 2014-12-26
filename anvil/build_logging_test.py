"""Test for the anvil logging components.
"""

__author__ = 'joshharrison@google.com'


import unittest2

from mock import call
from mock import MagicMock

from anvil import build_logging
from anvil import enums


class WorkUnitTest(unittest2.TestCase):

  def testRecordWorkUnits(self):
    work_unit = build_logging.WorkUnit('test')
    self.assertEquals(enums.Status.WAITING, work_unit.get_status())
    work_unit.total = 10
    self.assertEquals(10, work_unit.total)
    work_unit.complete = 10
    self.assertEquals(10, work_unit.complete)

  def testAddChildUnit(self):
    child = build_logging.WorkUnit('child')
    parent = build_logging.WorkUnit('parent')
    parent.add_child(child)
    self.assertEquals(parent, child.parent)
    self.assertEquals(1, len(parent.children))
    self.assertEquals(child, parent.children[0])

  def testAssumeChildCounts(self):
    child = build_logging.WorkUnit('child')
    parent = build_logging.WorkUnit('parent')
    parent.total = 100
    child.total = 50
    parent.add_child(child)
    self.assertEquals(150, parent.total)
    child.total = 250
    self.assertEquals(350, parent.total)
    # Test idempotence
    child.total = 250
    self.assertEquals(350, parent.total)
    parent.total = 200
    self.assertEquals(450, parent.total)

    sibling = build_logging.WorkUnit('sibling')
    grandchild = build_logging.WorkUnit('grandchild')
    grandchild.total = 10
    sibling.add_child(grandchild)
    self.assertEquals(10, sibling.total)
    parent.add_child(sibling)
    self.assertEquals(460, parent.total)
    grandchild.total = 100
    sibling.total = 200
    self.assertEquals(750, parent.total)

  def testInvalidCountsThrowsError(self):
    work_unit = build_logging.WorkUnit('test')
    work_unit.complete = 100
    with self.assertRaises(ValueError):
      work_unit.total = 50

  def testGetChildStatuses(self):
    child = build_logging.WorkUnit('child')
    parent = build_logging.WorkUnit('parent')
    parent.add_child(child)
    self.assertEquals(None, child.start_time)
    self.assertEquals(None, parent.start_time)
    self.assertEquals(enums.Status.WAITING, child.get_status())
    self.assertEquals(enums.Status.WAITING, parent.get_status())
    child.total = 20
    self.assertEquals(enums.Status.RUNNING, child.get_status())
    self.assertEquals(enums.Status.RUNNING, parent.get_status())
    parent.total = 30
    child.total = 0
    child.complete = 0
    self.assertEquals(enums.Status.SKIPPED, child.get_status())
    self.assertEquals(enums.Status.RUNNING, parent.get_status())
    parent.complete = 30
    self.assertEquals(enums.Status.SUCCEEDED, parent.get_status())

    child.exception = ValueError()
    self.assertEquals(enums.Status.FAILED, child.get_status())
    self.assertEquals(enums.Status.FAILED, parent.get_status())
    self.assertEquals(child.exception, parent.exception)

  def testChangeListenersCalled(self):
    mock_listener = MagicMock(name='listener')
    # If is_duplicate returns True, the listener will not be added to the
    # WorkUnit, and will therefor not have its handler triggered on
    # updates.
    mock_listener.is_duplicate.return_value = True
    test = build_logging.WorkUnit('test')
    test.add_change_listener(mock_listener)

    # Listeners should be triggered when updates occur anywhere along a WorkUnit
    # tree.
    child = build_logging.WorkUnit('child')
    parent = build_logging.WorkUnit('parent')
    parent.add_child(child)
    mock_child_listener = MagicMock(name='child_listener')
    mock_child_listener.is_duplicate.return_value = False
    mock_parent_listener = MagicMock(name='parent_listener')
    mock_parent_listener.is_duplicate.return_value = False
    child.add_change_listener(mock_child_listener)
    parent.add_change_listener(mock_parent_listener)

    mock_child_listener.mock_calls = []
    mock_parent_listener.mock_calls = []
    child.total = 100
    parent.total = 100
    parent.complete = 100
    expected_child_calls = [
      call.update(child, 'total', 100)
    ]
    expected_parent_calls = [
      call.update(parent, 'total', 100),
      call.update(parent, 'total', 200),
      call.update(parent, 'complete', 100)
    ]
    self.assertTrue(expected_child_calls == mock_child_listener.mock_calls)
    self.assertTrue(expected_parent_calls == mock_parent_listener.mock_calls)
    

if __name__ == '__main__':
  unittest2.main()
