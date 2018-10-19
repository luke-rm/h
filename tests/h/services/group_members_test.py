# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import mock
import pytest

from h.models import User, GroupScope
from h.services.group_members import GroupMembersService
from h.services.group_members import group_members_factory
from h.services.user import UserService
from tests.common.matchers import Matcher


class TestMemberJoin(object):

    def test_it_adds_user_to_group(self, svc, factories):
        user = factories.User()
        group = factories.Group()
        svc.member_join(group, user.userid)

        assert user in group.members

    def test_it_is_idempotent(self, svc, factories):
        user = factories.User()
        group = factories.Group()
        svc.member_join(group, user.userid)
        svc.member_join(group, user.userid)

        assert group.members.count(user) == 1

    def test_it_publishes_join_event(self, svc, factories, publish):
        group = factories.Group()
        user = factories.User()

        svc.member_join(group, user.userid)

        publish.assert_called_once_with('group-join', group.pubid, user.userid)


class TestMemberLeave(object):

    def test_it_removes_user_from_group(self, svc, factories, creator):
        group = factories.Group(creator=creator)
        new_member = factories.User()
        group.members.append(new_member)

        svc.member_leave(group, new_member.userid)

        assert new_member not in group.members

    def test_it_is_idempotent(self, svc, factories, creator):
        group = factories.Group(creator=creator)
        new_member = factories.User()
        group.members.append(new_member)

        svc.member_leave(group, new_member.userid)
        svc.member_leave(group, new_member.userid)

        assert new_member not in group.members

    def test_it_publishes_leave_event(self, svc, factories, publish):
        group = factories.Group()
        new_member = factories.User()
        group.members.append(new_member)

        svc.member_leave(group, new_member.userid)

        publish.assert_called_once_with('group-leave', group.pubid, new_member.userid)


class TestAddMembers(object):

    def test_it_adds_users_in_userids(self, factories, svc):
        group = factories.OpenGroup()
        users = [factories.User(), factories.User()]
        userids = [user.userid for user in users]

        svc.add_members(group, userids)

        assert group.members == users

    def test_it_does_not_remove_existing_members(self, factories, svc):
        creator = factories.User()
        group = factories.Group(creator=creator)
        users = [factories.User(), factories.User()]
        userids = [user.userid for user in users]

        svc.add_members(group, userids)

        assert len(group.members) == len(users) + 1  # account for creator user
        assert creator in group.members


class TestUpdateMembers(object):

    def test_it_adds_users_in_userids(self, factories, svc):
        group = factories.OpenGroup()  # no members at outset
        new_members = [
            factories.User(),
            factories.User()
        ]

        svc.update_members(group, [user.userid for user in new_members])

        assert group.members == new_members

    def test_it_removes_members_not_present_in_userids(self, factories, svc, creator):
        group = factories.Group(creator=creator)  # creator will be a member
        new_members = [
            factories.User(),
            factories.User()
        ]
        group.members.append(new_members[0])
        group.members.append(new_members[1])

        svc.update_members(group, [])

        assert not group.members  # including the creator

    def test_it_does_not_remove_members_present_in_userids(self, factories, svc, publish):
        group = factories.OpenGroup()  # no members at outset
        new_members = [
            factories.User(),
            factories.User()
        ]
        group.members.append(new_members[0])
        group.members.append(new_members[1])

        svc.update_members(group, [user.userid for user in group.members])

        assert new_members[0] in group.members
        assert new_members[1] in group.members
        publish.assert_not_called()

    def test_it_proxies_to_member_join_and_leave(self, factories, svc):
        svc.member_join = mock.Mock()
        svc.member_leave = mock.Mock()

        group = factories.OpenGroup()  # no members at outset
        new_members = [
            factories.User(),
            factories.User()
        ]
        group.members.append(new_members[0])

        svc.update_members(group, [new_members[1].userid])

        svc.member_join.assert_called_once_with(group, new_members[1].userid)
        svc.member_leave.assert_called_once_with(group, new_members[0].userid)

    def test_it_does_not_add_duplicate_members(self, factories, svc):
        # test for idempotency
        group = factories.OpenGroup()
        new_member = factories.User()

        svc.update_members(group, [new_member.userid, new_member.userid])

        assert group.members == [new_member]
        assert len(group.members) == 1


@pytest.mark.usefixtures('user_service')
class TestFactory(object):
    def test_returns_groups_service(self, pyramid_request):
        svc = group_members_factory(None, pyramid_request)

        assert isinstance(svc, GroupMembersService)

    def test_provides_request_db_as_session(self, pyramid_request):
        svc = group_members_factory(None, pyramid_request)

        assert svc.session == pyramid_request.db

    def test_wraps_user_service_as_user_fetcher(self, pyramid_request, user_service):
        svc = group_members_factory(None, pyramid_request)

        svc.user_fetcher('foo')

        user_service.fetch.assert_called_once_with('foo')

    def test_provides_realtime_publisher_as_publish(self, patch, pyramid_request):
        pyramid_request.realtime = mock.Mock(spec_set=['publish_user'])
        session = patch('h.services.group_members.session')
        svc = group_members_factory(None, pyramid_request)

        svc.publish('group-join', 'abc123', 'theresa')

        session.model.assert_called_once_with(pyramid_request)
        pyramid_request.realtime.publish_user.assert_called_once_with({
            'type': 'group-join',
            'session_model': session.model.return_value,
            'userid': 'theresa',
            'group': 'abc123',
        })


@pytest.fixture
def usr_svc(pyramid_request, db_session):
    def fetch(userid):
        # One doesn't want to couple to the user fetching service but
        # we do want to be able to fetch user models for internal
        # module behavior tests
        return db_session.query(User).filter_by(userid=userid).one_or_none()
    return fetch


@pytest.fixture
def origins():
    return ['http://example.com']


@pytest.fixture
def publish():
    return mock.Mock(spec_set=[])


@pytest.fixture
def svc(db_session, usr_svc, publish):
    return GroupMembersService(db_session, usr_svc, publish=publish)


@pytest.fixture
def creator(factories):
    return factories.User(username='group_creator')


@pytest.fixture
def user_service(pyramid_config):
    service = mock.create_autospec(UserService, spec_set=True, instance=True)
    pyramid_config.register_service(service, name='user')
    return service


class GroupScopeWithOrigin(Matcher):
    """Matches any GroupScope with the given origin."""

    def __init__(self, origin):
        self.origin = origin

    def __eq__(self, group_scope):
        if not isinstance(group_scope, GroupScope):
            return False
        return group_scope.origin == self.origin
